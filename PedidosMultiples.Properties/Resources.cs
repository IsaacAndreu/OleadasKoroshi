using System.CodeDom.Compiler;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Resources;
using System.Runtime.CompilerServices;

namespace PedidosMultiples.Properties
{
	[GeneratedCode("System.Resources.Tools.StronglyTypedResourceBuilder", "17.0.0.0")]
	[DebuggerNonUserCode]
	[CompilerGenerated]
	internal class Resources
	{
		private static ResourceManager resourceMan;

		private static CultureInfo resourceCulture;

		[EditorBrowsable(EditorBrowsableState.Advanced)]
		internal static ResourceManager ResourceManager
		{
			get
			{
				if (resourceMan == null)
				{
					resourceMan = new ResourceManager("PedidosMultiples.Properties.Resources", typeof(Resources).Assembly);
				}
				return resourceMan;
			}
		}

		[EditorBrowsable(EditorBrowsableState.Advanced)]
		internal static CultureInfo Culture
		{
			get
			{
				return resourceCulture;
			}
			set
			{
				resourceCulture = value;
			}
		}

		internal static UnmanagedMemoryStream alert => ResourceManager.GetStream("alert", resourceCulture);

		internal static UnmanagedMemoryStream alert_simple => ResourceManager.GetStream("alert_simple", resourceCulture);

		internal static Bitmap barcode_32x32 => (Bitmap)ResourceManager.GetObject("barcode_32x32", resourceCulture);

		internal static Bitmap changeBox => (Bitmap)ResourceManager.GetObject("changeBox", resourceCulture);

		internal static UnmanagedMemoryStream correct => ResourceManager.GetStream("correct", resourceCulture);

		internal static UnmanagedMemoryStream error => ResourceManager.GetStream("error", resourceCulture);

		internal static UnmanagedMemoryStream finalizar => ResourceManager.GetStream("finalizar", resourceCulture);

		internal static Bitmap LOGO_CODE => (Bitmap)ResourceManager.GetObject("LOGO_CODE", resourceCulture);

		internal static Bitmap LOGO_NATH => (Bitmap)ResourceManager.GetObject("LOGO_NATH", resourceCulture);

		internal static Bitmap LOGO_ORY => (Bitmap)ResourceManager.GetObject("LOGO_ORY", resourceCulture);

		internal static Bitmap LOGO_TCN => (Bitmap)ResourceManager.GetObject("LOGO_TCN", resourceCulture);

		internal static Bitmap LOGO_TUCTUC => (Bitmap)ResourceManager.GetObject("LOGO_TUCTUC", resourceCulture);

		internal static Bitmap pause_18x24 => (Bitmap)ResourceManager.GetObject("pause_18x24", resourceCulture);

		internal static Bitmap redo_24x24 => (Bitmap)ResourceManager.GetObject("redo_24x24", resourceCulture);

		internal static Bitmap timer_32x32 => (Bitmap)ResourceManager.GetObject("timer_32x32", resourceCulture);

		internal static Bitmap timer_restart_32x32 => (Bitmap)ResourceManager.GetObject("timer-restart_32x32", resourceCulture);

		internal Resources()
		{
		}
	}
}
