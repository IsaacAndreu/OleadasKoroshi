using System;
using System.Configuration;
using System.IO;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using PedidosMultiples;

// Prueba de ConnectionSQL contra un servidor PostgreSQL FALSO en 127.0.0.1 (nunca contra produccion).
// El servidor falso contesta a la peticion SSL con 'S' (acepta SSL) o 'N' (no tiene SSL), lee el mensaje de
// arranque y responde un error FATAL propio: si el cliente recibe ese error, la negociacion ha ido bien.
class Prueba
{
    static X509Certificate2 cert;
    static volatile string visto;

    static void Servidor(TcpListener l, bool conSsl)
    {
        while (true)
        {
            TcpClient c;
            try { c = l.AcceptTcpClient(); } catch { return; }
            try
            {
                Stream s = c.GetStream();
                var b = new BinaryReader(s);
                int len = Ent(b); int codigo = Ent(b);
                string ssl = "sin SSL";
                if (codigo == 80877103) // SSLRequest
                {
                    s.WriteByte((byte)(conSsl ? 'S' : 'N'));
                    if (conSsl)
                    {
                        var ss = new SslStream(s, false);
                        ss.AuthenticateAsServer(cert, false, SslProtocols.Tls12, false);
                        s = ss; ssl = "con SSL (" + ss.SslProtocol + ")"; b = new BinaryReader(s);
                    }
                    len = Ent(b); codigo = Ent(b);
                }
                b.ReadBytes(len - 8);
                visto = ssl;
                byte[] msg = System.Text.Encoding.ASCII.GetBytes("SFATAL\0C28P01\0Mservidor falso de prueba (" + ssl + ")\0\0");
                var w = new MemoryStream(); w.WriteByte((byte)'E'); var lb = BitConverter.GetBytes(msg.Length + 4); Array.Reverse(lb); w.Write(lb, 0, 4); w.Write(msg, 0, msg.Length);
                s.Write(w.ToArray(), 0, (int)w.Length); s.Flush();
                Thread.Sleep(200);
            }
            catch (Exception ex) { visto = "servidor: " + ex.GetType().Name; }
            finally { c.Close(); }
        }
    }
    static int Ent(BinaryReader b) { var x = b.ReadBytes(4); Array.Reverse(x); return BitConverter.ToInt32(x, 0); }

    static void Poner(string clave, string valor)
    {
        var cfg = ConfigurationManager.OpenExeConfiguration(ConfigurationUserLevel.None);
        cfg.AppSettings.Settings.Remove(clave);
        if (valor != null) cfg.AppSettings.Settings.Add(clave, valor);
        cfg.Save(ConfigurationSaveMode.Modified);
        ConfigurationManager.RefreshSection("appSettings");
    }

    static int fallos = 0;
    static void Caso(string nombre, string empresa, string ssl, int puerto, bool esperaOk)
    {
        string bd = empresa == "TTUC" ? "tuctuc" : "nath";
        Poner("db_host_" + bd, "127.0.0.1"); Poner("db_port_" + bd, puerto.ToString()); Poner("db_ssl_mode_" + bd, ssl);
        visto = null;
        using (var c = new ConnectionSQL(empresa))
        {
            var cb = new Npgsql.NpgsqlConnectionStringBuilder(c.dbConn.ConnectionString);
            if (cb.Host != "127.0.0.1") { Console.WriteLine("PARADO: host " + cb.Host + " no es local"); Environment.Exit(2); }
            string res;
            try { c.dbConn.Open(); res = "abierta?"; }
            catch (Npgsql.PostgresException ex) when (ex.SqlState == "28P01" && ex.MessageText.StartsWith("servidor falso")) { res = "OK negociado " + visto; }
            catch (Exception ex) { res = "ERROR " + ex.GetType().Name + ": " + ex.Message.Split('\n')[0]; }
            bool ok = res.StartsWith("OK") == esperaOk;
            if (!ok) fallos++;
            Console.WriteLine((ok ? "[bien] " : "[MAL]  ") + nombre + " | " + empresa + " SSL Mode=" + cb.SslMode + " Port=" + cb.Port + " -> " + res);
        }
    }

    // Uso contra un servidor de PRUEBA: prueba_ssl.exe <nath|tuctuc> <host> [puerto] [Prefer|Require|Disable]
    // Solo lee (version, base y si la conexion va con SSL). Se niega a conectar a las IP de produccion.
    static int Comprobar(string[] a)
    {
        string bd = a[0].ToLower(), host = a[1];
        string[] produccion = { "34.90.144.125", "104.199.5.207" };
        if (Array.IndexOf(produccion, host) >= 0) { Console.WriteLine("PARADO: " + host + " es produccion"); return 2; }
        if (bd != "nath" && bd != "tuctuc") { Console.WriteLine("La primera palabra debe ser nath o tuctuc"); return 2; }
        Poner("db_host_" + bd, host);
        Poner("db_port_" + bd, a.Length > 2 ? a[2] : "5432");
        Poner("db_ssl_mode_" + bd, a.Length > 3 ? a[3] : "Prefer");
        using (var c = new ConnectionSQL(bd == "tuctuc" ? "TTUC" : "NATH"))
        {
            var cb = new Npgsql.NpgsqlConnectionStringBuilder(c.dbConn.ConnectionString);
            if (Array.IndexOf(produccion, cb.Host) >= 0) { Console.WriteLine("PARADO: host de produccion"); return 2; }
            Console.WriteLine("Conectando a " + cb.Host + ":" + cb.Port + " SSL Mode=" + cb.SslMode + " base " + cb.Database);
            try
            {
                c.dbConn.Open();
                using (var cmd = new Npgsql.NpgsqlCommand("select version(), current_database(), coalesce((select ssl from pg_stat_ssl where pid = pg_backend_pid()), false)", c.dbConn))
                using (var r = cmd.ExecuteReader())
                {
                    r.Read();
                    Console.WriteLine("OK: " + r.GetString(0).Split(',')[0] + " | base " + r.GetString(1) + " | SSL: " + (r.GetBoolean(2) ? "si" : "no"));
                }
                return 0;
            }
            catch (Exception ex) { Console.WriteLine("ERROR " + ex.GetType().Name + ": " + ex.Message.Split((char)10)[0]); return 1; }
        }
    }

    static void Main(string[] args)
    {
        if (args.Length >= 2) { Environment.Exit(Comprobar(args)); }
        using (var rsa = RSA.Create(2048))
        {
            var req = new CertificateRequest("CN=prueba-local", rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
            var c0 = req.CreateSelfSigned(DateTimeOffset.Now.AddDays(-1), DateTimeOffset.Now.AddDays(1));
            cert = new X509Certificate2(c0.Export(X509ContentType.Pfx, "x"), "x", X509KeyStorageFlags.Exportable);
        }
        var sinSsl = new TcpListener(IPAddress.Loopback, 0); sinSsl.Start();
        var conSsl = new TcpListener(IPAddress.Loopback, 0); conSsl.Start();
        int pN = ((IPEndPoint)sinSsl.LocalEndpoint).Port, pS = ((IPEndPoint)conSsl.LocalEndpoint).Port;
        new Thread(() => Servidor(sinSsl, false)) { IsBackground = true }.Start();
        new Thread(() => Servidor(conSsl, true)) { IsBackground = true }.Start();

        Caso("servidor sin SSL, Prefer (como hoy)", "TTUC", "Prefer", pN, true);
        Caso("servidor con SSL, Prefer", "TTUC", "Prefer", pS, true);
        Caso("servidor con SSL, Require", "TTUC", "Require", pS, true);
        Caso("servidor sin SSL, Require (debe fallar)", "TTUC", "Require", pN, false);
        Caso("servidor con SSL, Disable", "TTUC", "Disable", pS, true);
        Caso("NATH: servidor con SSL, Require", "NATH", "Require", pS, true);
        Caso("NATH: servidor sin SSL, Prefer", "NATH", "Prefer", pN, true);
        Caso("valor SSL mal escrito -> Prefer", "TTUC", "requiere", pS, true);

        // Sin claves en el .config: debe salir el host de siempre (solo se mira la cadena, NO se conecta)
        foreach (var k in new[] { "db_host_nath", "db_port_nath", "db_ssl_mode_nath", "db_host_tuctuc", "db_port_tuctuc", "db_ssl_mode_tuctuc" }) Poner(k, null);
        foreach (var e in new[] { "TTUC", "NATH" })
            using (var c = new ConnectionSQL(e))
            {
                var cb = new Npgsql.NpgsqlConnectionStringBuilder(c.dbConn.ConnectionString);
                Console.WriteLine("[sin claves, no conecta] " + e + " -> Host=" + cb.Host + " Port=" + cb.Port + " SSL Mode=" + cb.SslMode);
            }
        Poner("db_port_tuctuc", "abc");
        using (var c = new ConnectionSQL("TTUC")) { var cb = new Npgsql.NpgsqlConnectionStringBuilder(c.dbConn.ConnectionString); Console.WriteLine("[puerto mal escrito, no conecta] Port=" + cb.Port); }
        Console.WriteLine(fallos == 0 ? "TODO BIEN" : "FALLOS: " + fallos);
    }
}
