using System;
using System.Net;
using CookComputing.XmlRpc;

namespace PedidosMultiples
{
	// Ejecuta una accion de servidor de Odoo 13 (ir.actions.server) por XML-RPC,
	// de forma sincrona, sobre un albaran. La usa el modo matricula de KOROSHI (EFFE)
	// para empaquetar la caja cerrada con el nombre de la matricula.
	public class OdooAccion
	{
		public class Resultado
		{
			public bool Ok;

			public string Mensaje = string.Empty;

			// Matricula que devuelve la accion en action['matricula'] (si la genera Odoo)
			public string Matricula = string.Empty;
		}

		private readonly string url;

		private readonly string db;

		private readonly string username;

		private readonly string password;

		private readonly int timeoutMs;

		private int uid;

		public OdooAccion(string url, string db, string username, string password, int timeoutSeg)
		{
			this.url = (url ?? string.Empty).TrimEnd('/');
			this.db = db;
			this.username = username;
			this.password = password;
			timeoutMs = ((timeoutSeg > 0) ? timeoutSeg : 30) * 1000;
		}

		public static OdooAccion DesdeConfiguracion()
		{
			int.TryParse(InitialForm.ReturnSetting("odoo_timeout_seg"), out var timeoutSeg);
			return new OdooAccion(InitialForm.ReturnSetting("odoo_url"), InitialForm.ReturnSetting("odoo_db"), InitialForm.ReturnSetting("odoo_user"), InitialForm.ReturnSetting("odoo_password"), timeoutSeg);
		}

		public bool EstaConfigurada()
		{
			return Valido(url) && Valido(db) && Valido(username) && Valido(password);
		}

		private static bool Valido(string valor)
		{
			return !string.IsNullOrWhiteSpace(valor) && valor != "Not Found";
		}

		private IOdooModels Modelos()
		{
			IOdooModels models = XmlRpcProxyGen.Create<IOdooModels>();
			models.Url = url + "/xmlrpc/2/object";
			models.Timeout = timeoutMs;
			return models;
		}

		private void Autenticar()
		{
			if (uid > 0)
			{
				return;
			}
			IOdooCommon common = XmlRpcProxyGen.Create<IOdooCommon>();
			common.Url = url + "/xmlrpc/2/common";
			common.Timeout = timeoutMs;
			try
			{
				uid = common.Authenticate(db, username, password, new XmlRpcStruct());
			}
			catch (XmlRpcTypeMismatchException)
			{
				// Odoo devuelve False (no un entero) si el usuario o la contrasena no son correctos
				uid = 0;
			}
			if (uid <= 0)
			{
				throw new Exception("Usuario o contraseña de Odoo incorrectos (odoo_user / odoo_password)");
			}
		}

		// Devuelve el id del albaran por nombre y empresa, o 0 si no existe.
		public int BuscarPickingId(string nombre, int companyId)
		{
			Autenticar();
			object[] domain = new object[2]
			{
				new object[3] { "name", "=", nombre },
				new object[3] { "company_id", "=", companyId }
			};
			XmlRpcStruct kwargs = new XmlRpcStruct
			{
				{ "limit", 1 },
				{ "context", ContextoEmpresa(companyId) }
			};
			object[] ids = (object[])Modelos().ExecuteKw(db, uid, password, "stock.picking", "search", new object[1] { domain }, kwargs);
			return (ids.Length > 0) ? Convert.ToInt32(ids[0]) : 0;
		}

		// Ejecuta la accion de servidor accionId sobre el albaran pickingId.
		// En el contexto van active_model, active_id, active_ids y los valores de extra.
		// Nunca lanza excepcion: el error de Odoo vuelve en Resultado.Mensaje.
		public Resultado EjecutarAccion(int accionId, int pickingId, int companyId, XmlRpcStruct extra)
		{
			Resultado resultado = new Resultado();
			try
			{
				if (!EstaConfigurada())
				{
					throw new Exception("Falta configurar odoo_url / odoo_db / odoo_user / odoo_password");
				}
				if (accionId <= 0)
				{
					throw new Exception("Falta configurar odoo_accion_empaquetar_id");
				}
				Autenticar();
				XmlRpcStruct contexto = ContextoEmpresa(companyId);
				contexto.Add("active_model", "stock.picking");
				contexto.Add("active_id", pickingId);
				contexto.Add("active_ids", new int[1] { pickingId });
				if (extra != null)
				{
					foreach (string clave in extra.Keys)
					{
						contexto[clave] = extra[clave];
					}
				}
				XmlRpcStruct kwargs = new XmlRpcStruct { { "context", contexto } };
				object respuesta = Modelos().ExecuteKw(db, uid, password, "ir.actions.server", "run", new object[1] { new int[1] { accionId } }, kwargs);
				if (respuesta is XmlRpcStruct accion && accion.ContainsKey("matricula") && accion["matricula"] != null)
				{
					resultado.Matricula = accion["matricula"].ToString();
				}
				resultado.Ok = true;
				resultado.Mensaje = "OK";
			}
			catch (XmlRpcFaultException ex)
			{
				resultado.Mensaje = MensajeOdoo(ex.FaultString);
				ExceptionLogging.LogExceptionToFile(ex);
			}
			catch (WebException ex2)
			{
				resultado.Mensaje = "Sin conexión con Odoo: " + ex2.Message;
				ExceptionLogging.LogExceptionToFile(ex2);
			}
			catch (Exception ex3)
			{
				resultado.Mensaje = ex3.Message;
				ExceptionLogging.LogExceptionToFile(ex3);
			}
			return resultado;
		}

		// Igual que EjecutarAccion, pero buscando antes el albaran por nombre.
		public Resultado EjecutarAccionPorNombre(int accionId, string nombreAlbaran, int companyId, XmlRpcStruct extra)
		{
			try
			{
				if (!EstaConfigurada())
				{
					throw new Exception("Falta configurar odoo_url / odoo_db / odoo_user / odoo_password");
				}
				int pickingId = BuscarPickingId(nombreAlbaran, companyId);
				if (pickingId <= 0)
				{
					throw new Exception("No se encuentra el albarán " + nombreAlbaran + " en Odoo");
				}
				return EjecutarAccion(accionId, pickingId, companyId, extra);
			}
			catch (XmlRpcFaultException ex)
			{
				ExceptionLogging.LogExceptionToFile(ex);
				return new Resultado
				{
					Mensaje = MensajeOdoo(ex.FaultString)
				};
			}
			catch (WebException ex2)
			{
				ExceptionLogging.LogExceptionToFile(ex2);
				return new Resultado
				{
					Mensaje = "Sin conexión con Odoo: " + ex2.Message
				};
			}
			catch (Exception ex3)
			{
				ExceptionLogging.LogExceptionToFile(ex3);
				return new Resultado
				{
					Mensaje = ex3.Message
				};
			}
		}

		private static XmlRpcStruct ContextoEmpresa(int companyId)
		{
			return new XmlRpcStruct
			{
				{ "allowed_company_ids", new int[1] { companyId } },
				{ "force_company", companyId }
			};
		}

		// Odoo devuelve el texto del Warning/UserError tal cual, o una traza entera
		// si es otro error: en ese caso se queda la ultima linea no vacia.
		private static string MensajeOdoo(string faultString)
		{
			if (string.IsNullOrWhiteSpace(faultString))
			{
				return "Error de Odoo sin mensaje";
			}
			string texto = faultString.Trim();
			if (!texto.Contains("Traceback"))
			{
				return texto;
			}
			string[] lineas = texto.Split(new char[2] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
			return lineas[lineas.Length - 1].Trim();
		}
	}
}
