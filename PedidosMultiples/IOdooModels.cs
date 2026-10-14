using CookComputing.XmlRpc;

namespace PedidosMultiples
{
	public interface IOdooModels : IXmlRpcProxy
	{
		[XmlRpcMethod("execute_kw")]
		object ExecuteKw(string db, int uid, string password, string model, string method, object[] parameters);

		[XmlRpcMethod("execute_kw")]
		object ExecuteKw(string db, int uid, string password, string model, string method, object[] parameters, XmlRpcStruct kwargs);
	}
}
