using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Npgsql;

namespace PedidosMultiples
{
	internal class ConnectionSQL : IDisposable
	{
		private IntPtr handle;

		public NpgsqlConnection dbConn;

		private string connectionString;

		private bool disposed;

		public ConnectionSQL(string company)
		{
			try
			{
				if (!company.Equals("TTUC") && !company.Equals("ALAN") && !company.Equals("CODE"))
				{
					connectionString = "Host=34.90.144.125;Username=nath_write;Password=_@22nath;Database=NATH_PRODUCTION";
				}
				else
				{
					connectionString = "Host=104.199.5.207;Username=tuctuc_write;Password=_@1tuctuc;Database=TUCTUC_PRODUCTION";
				}
				dbConn = new NpgsqlConnection(connectionString);
			}
			catch (Exception ex)
			{
				MessageBox.Show("ConnectionSQL_ " + ex);
			}
		}

		public void Dispose()
		{
			Dispose(disposing: true);
			GC.SuppressFinalize(this);
		}

		protected virtual void Dispose(bool disposing)
		{
			if (!disposed)
			{
				if (disposing)
				{
					dbConn.Dispose();
				}
				CloseHandle(handle);
				handle = IntPtr.Zero;
				disposed = true;
			}
		}

		[DllImport("Kernel32")]
		private static extern bool CloseHandle(IntPtr handle);

		~ConnectionSQL()
		{
			Dispose(disposing: false);
		}
	}
}
