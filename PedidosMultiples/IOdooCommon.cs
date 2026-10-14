using CookComputing.XmlRpc;

namespace PedidosMultiples
{
	public interface IOdooCommon : IXmlRpcProxy
	{
		[XmlRpcMethod("authenticate")]
		int Authenticate(string db, string username, string password, XmlRpcStruct emptyParams);
	}
}
