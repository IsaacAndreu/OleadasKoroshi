using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace PedidosMultiples
{
	internal class ExceptionLogging
	{
		private static readonly string LogDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ExceptionLogs");

		private static readonly string LogFileName = "ApplicationErrors.log";

		private static readonly string LogFilePath = Path.Combine(LogDirectory, LogFileName);

		private static readonly object _logLock = new object();

		public static void LogExceptionToFile(Exception ex, string additionalInfo = null)
		{
			if (!Directory.Exists(LogDirectory))
			{
				Directory.CreateDirectory(LogDirectory);
			}
			StringBuilder logEntry = new StringBuilder();
			logEntry.AppendLine($"Timestamp: {DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}");
			logEntry.AppendLine($"Thread ID: {Thread.CurrentThread.ManagedThreadId}");
			logEntry.AppendLine("Exception Type: " + ex.GetType().FullName);
			logEntry.AppendLine("Message: " + ex.Message);
			if (!string.IsNullOrEmpty(additionalInfo))
			{
				logEntry.AppendLine("Additional Info: " + additionalInfo);
			}
			if (ex is WebException webEx)
			{
				logEntry.AppendLine($"WebException Status: {webEx.Status}");
				if (webEx.Response is HttpWebResponse httpResponse)
				{
					logEntry.AppendLine($"HTTP Status Code: {(int)httpResponse.StatusCode} {httpResponse.StatusDescription}");
					try
					{
						using (Stream responseStream = httpResponse.GetResponseStream())
						{
							if (responseStream != null && responseStream.CanRead)
							{
								using (StreamReader reader = new StreamReader(responseStream))
								{
									string errorBody = reader.ReadToEnd();
									if (!string.IsNullOrEmpty(errorBody))
									{
										logEntry.AppendLine("Error Response Body: " + errorBody.Substring(0, Math.Min(errorBody.Length, 500)));
									}
								}
							}
						}
					}
					catch (Exception ex2)
					{
						logEntry.AppendLine("WARNING: Could not read error response body: " + ex2.Message);
					}
				}
			}
			logEntry.AppendLine("Stack Trace: " + ex.StackTrace);
			Exception innerEx = ex.InnerException;
			int innerExCount = 0;
			while (innerEx != null)
			{
				innerExCount++;
				logEntry.AppendLine($"--- Inner Exception {innerExCount} ---");
				logEntry.AppendLine("Inner Exception Type: " + innerEx.GetType().FullName);
				logEntry.AppendLine("Inner Exception Message: " + innerEx.Message);
				logEntry.AppendLine("Inner Exception Stack Trace: " + innerEx.StackTrace);
				innerEx = innerEx.InnerException;
			}
			logEntry.AppendLine("------------------------------------------------------------------");
			try
			{
				lock (_logLock)
				{
					File.AppendAllText(LogFilePath, logEntry.ToString());
				}
			}
			catch (Exception)
			{
				MessageBox.Show(logEntry.ToString());
			}
		}
	}
}
