using System.Collections.Generic;

namespace PedidosMultiples
{
	internal class CourierRequest
	{
		public Origen origen { get; set; }

		public Destino destino { get; set; }

		public Datos datos { get; set; }

		public Dictionary<string, bool> opciones { get; set; }

		public string referencia { get; set; }
	}
}
