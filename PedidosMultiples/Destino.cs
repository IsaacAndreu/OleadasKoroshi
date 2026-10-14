namespace PedidosMultiples
{
	internal class Destino
	{
		public string nombre { get; set; }

		public string direccion { get; set; }

		public string observaciones { get; set; }

		public string codigo_postal { get; set; }

		public string localidad { get; set; }

		public string pais { get; set; }

		public Contacto contacto { get; set; }
	}
}
