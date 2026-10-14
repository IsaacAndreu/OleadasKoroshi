using System;
using System.Collections.Generic;
using System.Configuration;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;
using System.Xml;
using Newtonsoft.Json;
using Npgsql;

namespace PedidosMultiples
{
	internal class Envios
	{
		public string queryGetClientData = "select entrega.name as Name, entrega.nombre_padre, CONCAT(entrega.street, ' ', entrega.street2) as Address, entrega.zip as CodePostal, entrega.city as Ville, entrega.country as Pays, coalesce(entrega.phone_sanitized, '') as Telephone, coalesce(entrega.email_normalized, '') as Email,sp.note, sp.origin, sp.x_studio_order_remarks as remarks, mirakl.shipping_type_label as shipping_type_label, entrega.province_code as province_code,entrega.country_code as country_code, carrier.name as carrier, sp.carrier_tracking_ref as carrier_tracking from stock_picking sp left join res_company rc on rc.id = sp.company_id left join (   select rp.id, rp.name, (select rp2.name from res_partner rp2 where rp2.id = rp.parent_id) as nombre_padre,    rp.contact_address_complete, rp.street, rp.street2, rp.zip, rp.city,    rcs2.name as province,    rcs2.code as province_code,    rc.name as country,    rc.code as country_code,    rp.email_normalized, coalesce(rp.phone_sanitized, rp.phone) as phone_sanitized, rp.old_code as cod_sage    from res_partner rp    left join res_country rc on rc.id = rp.country_id    left join res_country_state rcs2 on rcs2.id = rp.state_id) as entrega on entrega.id = sp.partner_id left join (   select so.id as pedido, so.mirakl_mapping_id, mof.shipping_type_label    from sale_order so    left join mirakl_order_mapping mom on mom.id = so.mirakl_mapping_id    left join mirakl_order_feed mof on mof.id = mom.odoo_feed ) as mirakl on mirakl.pedido = sp.sale_id left join (   select dc.id, dc.name    from delivery_carrier dc ) as carrier on carrier.id = sp.carrier_id where sp.name = (@order) and sp.company_id = (@company_id) and sp.state = 'done';";

		public string queryUpdateOrderTracking = "update stock_picking set carrier_tracking_ref = (@tracking_num), carrier_id = (select id from delivery_carrier where name like (@carrier_name) and company_id = (@company_id)), date_shipped = (@date_shipped), delivery_state = (@delivery_state), is_sent = true where name = (@order) and company_id = (@company_id)";

		private int db { get; set; }

		private string company { get; set; }

		private string compName { get; set; }

		private string compNif { get; set; }

		private string shopId { get; set; }

		private string eciKey { get; set; }

		private string eciDocType { get; set; }

		private string eciUrl { get; set; }

		private string eciDocUrl { get; set; }

		private string eciOrderNumber { get; set; }

		private string eciEntrega { get; set; }

		private string compAddress { get; set; }

		private string compTlf { get; set; }

		private string compCountry { get; set; }

		private string compZip { get; set; }

		private string compCity { get; set; }

		private string sendingShipmentUrl { get; set; }

		private string sendingUser { get; set; }

		private string sendingPwd { get; set; }

		private string correosExpShipmentUrl { get; set; }

		private string correosExpUser { get; set; }

		private string correosExpPwd { get; set; }

		private string correosExpUserCode { get; set; }

		private string nacexUsername { get; set; }

		private string nacexPwd { get; set; }

		private string nacexAgency { get; set; }

		private string nacexServiceCode { get; set; }

		private string nacexCarriageCode { get; set; }

		private string nacexPackagingCode { get; set; }

		private string nacexTipPre1 { get; set; }

		private string nacexRecipPre1 { get; set; }

		private string nacexUrl { get; set; }

		private string nacexCustomerCode { get; set; }

		public Dictionary<string, int> databases { get; set; }

		public Dictionary<string, string> apiTokens { get; set; }

		public Dictionary<string, string> companyNames { get; set; }

		public Dictionary<string, string> companyNifs { get; set; }

		public Dictionary<string, string> eciApiKeys { get; set; }

		public Dictionary<string, string> eciShopIds { get; set; }

		public Dictionary<string, string> sendingUsers { get; set; }

		public Dictionary<string, string> sendingPwds { get; set; }

		public Dictionary<string, string> cexUsers { get; set; }

		public Dictionary<string, string> cexPwds { get; set; }

		public Dictionary<string, string> cexUserCodes { get; set; }

		public Dictionary<string, string> nacexCustomerCodes { get; set; }

		public int pesoBulto { get; set; }

		public int cantidadBultos { get; set; } = 1;

		public double volumen { get; set; }

		public string printer { get; set; }

		public string carrier { get; set; }

		public Envios()
		{
			databases = new Dictionary<string, int>();
			apiTokens = new Dictionary<string, string>();
			companyNames = new Dictionary<string, string>();
			companyNifs = new Dictionary<string, string>();
			eciApiKeys = new Dictionary<string, string>();
			eciShopIds = new Dictionary<string, string>();
			sendingUsers = new Dictionary<string, string>();
			sendingPwds = new Dictionary<string, string>();
			cexUsers = new Dictionary<string, string>();
			cexPwds = new Dictionary<string, string>();
			cexUserCodes = new Dictionary<string, string>();
			nacexCustomerCodes = new Dictionary<string, string>();
			InitializeData();
		}

		private void InitializeData()
		{
			eciApiKeys.Add("NATH", string.Empty);
			eciApiKeys.Add("ALAN", ConfigurationManager.AppSettings["ory_eci"]);
			eciApiKeys.Add("CAREY", ConfigurationManager.AppSettings["ory_eci"]);
			eciApiKeys.Add("CODE", ConfigurationManager.AppSettings["code_eci"]);
			eciApiKeys.Add("TCN", ConfigurationManager.AppSettings["tcn_eci"]);
			eciApiKeys.Add("TTUC", ConfigurationManager.AppSettings["ttuc_eci"]);
			eciApiKeys.Add("EFFE", string.Empty);
			eciShopIds.Add("NATH", string.Empty);
			eciShopIds.Add("ALAN", ConfigurationManager.AppSettings["ory_id"]);
			eciShopIds.Add("CAREY", ConfigurationManager.AppSettings["ory_id"]);
			eciShopIds.Add("CODE", ConfigurationManager.AppSettings["code_id"]);
			eciShopIds.Add("TCN", ConfigurationManager.AppSettings["tcn_id"]);
			eciShopIds.Add("TTUC", ConfigurationManager.AppSettings["ttuc_id"]);
			eciShopIds.Add("EFFE", string.Empty);
			eciDocType = ConfigurationManager.AppSettings["doc_type"];
			eciUrl = ConfigurationManager.AppSettings["eci_url"];
			eciDocUrl = ConfigurationManager.AppSettings["eci_doc_url"];
			sendingUsers.Add("NATH", string.Empty);
			sendingUsers.Add("ALAN", ConfigurationManager.AppSettings["sending_user_mi"]);
			sendingUsers.Add("CAREY", ConfigurationManager.AppSettings["sending_user_mi"]);
			sendingUsers.Add("CODE", string.Empty);
			sendingUsers.Add("TCN", string.Empty);
			sendingUsers.Add("TTUC", ConfigurationManager.AppSettings["sending_user"]);
			sendingUsers.Add("EFFE", string.Empty);
			sendingPwds.Add("NATH", string.Empty);
			sendingPwds.Add("ALAN", ConfigurationManager.AppSettings["sending_pwd_mi"]);
			sendingPwds.Add("CAREY", ConfigurationManager.AppSettings["sending_pwd_mi"]);
			sendingPwds.Add("CODE", string.Empty);
			sendingPwds.Add("TCN", string.Empty);
			sendingPwds.Add("TTUC", ConfigurationManager.AppSettings["sending_pwd"]);
			sendingPwds.Add("EFFE", string.Empty);
			sendingShipmentUrl = ConfigurationManager.AppSettings["sending_url"];
			cexUsers.Add("NATH", ConfigurationManager.AppSettings["correosExp_user_tt"]);
			cexUsers.Add("ALAN", ConfigurationManager.AppSettings["correosExp_user_mi"]);
			cexUsers.Add("CAREY", ConfigurationManager.AppSettings["correosExp_user_mi"]);
			cexUsers.Add("CODE", ConfigurationManager.AppSettings["correosExp_user_ub"]);
			cexUsers.Add("TCN", ConfigurationManager.AppSettings["correosExp_user_gc"]);
			cexUsers.Add("TTUC", ConfigurationManager.AppSettings["correosExp_user_tt"]);
			cexUsers.Add("EFFE", string.Empty);
			cexPwds.Add("NATH", ConfigurationManager.AppSettings["correosExp_pwd_tt"]);
			cexPwds.Add("ALAN", ConfigurationManager.AppSettings["correosExp_pwd_mi"]);
			cexPwds.Add("CAREY", ConfigurationManager.AppSettings["correosExp_pwd_mi"]);
			cexPwds.Add("CODE", ConfigurationManager.AppSettings["correosExp_pwd_ub"]);
			cexPwds.Add("TCN", ConfigurationManager.AppSettings["correosExp_pwd_gc"]);
			cexPwds.Add("TTUC", ConfigurationManager.AppSettings["correosExp_pwd_tt"]);
			cexPwds.Add("EFFE", string.Empty);
			cexUserCodes.Add("NATH", ConfigurationManager.AppSettings["correosExp_userCode_tt"]);
			cexUserCodes.Add("ALAN", ConfigurationManager.AppSettings["correosExp_userCode_mi"]);
			cexUserCodes.Add("CAREY", ConfigurationManager.AppSettings["correosExp_userCode_mi"]);
			cexUserCodes.Add("CODE", ConfigurationManager.AppSettings["correosExp_userCode_ub"]);
			cexUserCodes.Add("TCN", ConfigurationManager.AppSettings["correosExp_userCode_gc"]);
			cexUserCodes.Add("TTUC", ConfigurationManager.AppSettings["correosExp_userCode_tt"]);
			cexUserCodes.Add("EFFE", string.Empty);
			correosExpShipmentUrl = ConfigurationManager.AppSettings["correosExp_url"];
			nacexCustomerCodes.Add("NATH", ConfigurationManager.AppSettings["nacex_customer_code_tt"]);
			nacexCustomerCodes.Add("ALAN", ConfigurationManager.AppSettings["nacex_customer_code_mi"]);
			nacexCustomerCodes.Add("CAREY", ConfigurationManager.AppSettings["nacex_customer_code_mi"]);
			nacexCustomerCodes.Add("CODE", ConfigurationManager.AppSettings["nacex_customer_code_ub"]);
			nacexCustomerCodes.Add("TCN", string.Empty);
			nacexCustomerCodes.Add("TTUC", ConfigurationManager.AppSettings["nacex_customer_code_tt"]);
			nacexCustomerCodes.Add("EFFE", string.Empty);
			nacexUsername = ConfigurationManager.AppSettings["nacex_username"];
			nacexPwd = ConfigurationManager.AppSettings["nacex_pwd"];
			nacexAgency = ConfigurationManager.AppSettings["nacex_agency"];
			nacexServiceCode = ConfigurationManager.AppSettings["nacex_service_code"];
			nacexCarriageCode = ConfigurationManager.AppSettings["nacex_carriage_code"];
			nacexPackagingCode = ConfigurationManager.AppSettings["nacex_packaging_code"];
			nacexTipPre1 = ConfigurationManager.AppSettings["nacex_tip_pre1"];
			nacexRecipPre1 = ConfigurationManager.AppSettings["nacex_recip_pre1"];
			nacexUrl = ConfigurationManager.AppSettings["nacex_url"];
			compAddress = ConfigurationManager.AppSettings["comp_address"];
			compTlf = ConfigurationManager.AppSettings["comp_tlf"];
			compCountry = ConfigurationManager.AppSettings["comp_country"];
			compZip = ConfigurationManager.AppSettings["comp_zip"];
			compCity = ConfigurationManager.AppSettings["comp_city"];
			companyNames.Add("NATH", "NATH 2004 SL");
			companyNames.Add("ALAN", "MODA INTIMA 1964 SL");
			companyNames.Add("CAREY", "CAREY PERFECT FIT SL");
			companyNames.Add("CODE", "UNITED BRANDS 2015 SL");
			companyNames.Add("TCN", "GOLMAR COLLECTIONS SL");
			companyNames.Add("TTUC", "NATH 2004, S.L.");
			companyNames.Add("EFFE", "EFFECTIVE LOGISTICS, S.L.");
			companyNifs.Add("NATH", "B50988492");
			companyNifs.Add("ALAN", "B43911403");
			companyNifs.Add("CAREY", "B09603614");
			companyNifs.Add("CODE", "B55667497");
			companyNifs.Add("TCN", "B12817391");
			companyNifs.Add("TTUC", "B50988492");
			companyNifs.Add("EFFE", "B55711907");
			pesoBulto = Convert.ToInt32(ConfigurationManager.AppSettings["peso_bulto"]);
			volumen = Convert.ToDouble(ConfigurationManager.AppSettings["volumen_bulto"]);
		}

		public void SetCompanyVariablesEnvios(string companyName, int companyId)
		{
			company = companyName;
			db = companyId;
			compName = companyNames[companyName];
			compNif = companyNifs[companyName];
			shopId = eciShopIds[companyName];
			eciKey = eciApiKeys[companyName];
			sendingUser = sendingUsers[companyName];
			sendingPwd = sendingPwds[companyName];
			correosExpUser = cexUsers[companyName];
			correosExpPwd = cexPwds[companyName];
			correosExpUserCode = cexUserCodes[companyName];
			nacexCustomerCode = nacexCustomerCodes[companyName];
		}

		private string CreateMD5Hash(string input)
		{
			MD5 mD = MD5.Create();
			byte[] inputBytes = Encoding.ASCII.GetBytes(input);
			byte[] hashBytes = mD.ComputeHash(inputBytes);
			StringBuilder sb = new StringBuilder();
			for (int i = 0; i < hashBytes.Length; i++)
			{
				sb.Append(hashBytes[i].ToString("X2"));
			}
			return sb.ToString();
		}

		public string ValidateOrder(string order, int companyId, int carrierId, int packageTypeId)
		{
			string filename = string.Empty;
			string db = "TUCTUC_PRODUCTION";
			string username = "oleadas@a.es";
			string password = "84WyupDgtaHRG%";
			OdooClient client = new OdooClient("https://odoo.tuctuc.com", db, username, password);
			try
			{
				if (client.FetchOdooUid() != 0)
				{
					Tuple<int, string, string> result = client.CheckIfOperationExists(order, companyId, carrierId, packageTypeId);
					if (result.Item1 > 0 && result.Item2 != string.Empty && result.Item3 != string.Empty)
					{
						filename = result.Item3;
					}
				}
			}
			catch (Exception ex)
			{
				ExceptionLogging.LogExceptionToFile(ex);
				MessageBox.Show("ValidateOrder " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return filename;
		}

		private Tuple<Destino, string> FetchClientData(string database, string peCode)
		{
			try
			{
				eciOrderNumber = string.Empty;
				eciEntrega = string.Empty;
				string retorno = string.Empty;
				Destino destination = new Destino();
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryGetClientData, cSql.dbConn);
					npgsqlCommand.Parameters.AddWithValue("@order", peCode);
					npgsqlCommand.Parameters.AddWithValue("@company_id", db);
					NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
					if (!reader.HasRows)
					{
						MessageBox.Show("FetchClientData: REVISAR LA TRANSFERENCIA, SI NO ESTA VALIDADA NO SE PUEDE ENVIAR.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
						return null;
					}
					reader.Read();
					if (!reader["origin"].ToString().ToLower().StartsWith("ds-") || !reader["origin"].ToString().ToLower().StartsWith("vp-") || !reader["origin"].ToString().ToLower().StartsWith("eci-") || !reader["origin"].ToString().ToLower().StartsWith("srp-") || !reader["origin"].ToString().ToLower().StartsWith("w") || !reader["origin"].ToString().ToLower().StartsWith("vbd-"))
					{
						return null;
					}
					if (reader["name"].ToString().Length > 0)
					{
						destination.nombre = reader["name"].ToString();
					}
					else
					{
						if (reader["nombre_padre"].ToString().Length <= 0)
						{
							MessageBox.Show("FetchClientData: REVISAR NOMBRE DEL CLIENTE.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
							return null;
						}
						destination.nombre = reader["nombre_padre"].ToString();
					}
					if (reader["shipping_type_label"].ToString().Length > 0)
					{
						eciEntrega = reader["shipping_type_label"].ToString();
					}
					if (eciEntrega.Equals("Entrega en centro comercial") && reader["origin"].ToString().ToLower().Contains("eci-") && reader["remarks"].ToString().Length > 0)
					{
						if (reader["remarks"].ToString().Contains("-A"))
						{
							eciOrderNumber = reader["remarks"].ToString();
						}
						else
						{
							eciOrderNumber = reader["remarks"].ToString() + "-A";
						}
					}
					if (reader["address"].ToString().Length <= 0 || reader["codepostal"].ToString().Length <= 0 || reader["telephone"].ToString().Length <= 0)
					{
						MessageBox.Show("FetchClientData: REVISAR LA DIRECCION, CODIGO POSTAL O TELEFONO.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
						return null;
					}
					retorno = ((!reader["note"].ToString().ToLower().Contains("pedido reposición") && !reader["note"].ToString().ToLower().Contains("pedido reposicion") && !reader["note"].ToString().ToLower().Contains("pedido retorno") && !reader["note"].ToString().ToLower().Contains("retorno")) ? "" : reader["note"].ToString());
					destination.direccion = reader["address"].ToString();
					if (reader["origin"].ToString().ToLower().StartsWith("ds-"))
					{
						destination.observaciones = "TUC TUC BY SHOWROOMPRIVE";
					}
					else
					{
						destination.observaciones = string.Empty;
					}
					if (reader["pays"].ToString().Equals("Spain") && reader["codepostal"].ToString().Length < 5)
					{
						destination.codigo_postal = reader["codepostal"].ToString().PadLeft(5, '0');
					}
					else
					{
						destination.codigo_postal = reader["codepostal"].ToString();
					}
					destination.localidad = reader["ville"].ToString();
					if (reader["pays"].ToString().Equals("Spain"))
					{
						destination.pais = "ES";
					}
					else
					{
						if (!reader["pays"].ToString().Equals("Portugal"))
						{
							MessageBox.Show("FetchClientData: PAIS NO ES ESPAÑA NI PORTUGAL.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
							return null;
						}
						destination.pais = "PT";
					}
					Contacto cont = new Contacto
					{
						nombre = reader["name"].ToString(),
						email = reader["email"].ToString(),
						telefono = reader["telephone"].ToString()
					};
					destination.contacto = cont;
					reader.Close();
					cSql.dbConn.Close();
				}
				return new Tuple<Destino, string>(destination, retorno);
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("FetchClientData: " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes)
				{
					FetchClientData(database, peCode);
				}
				return null;
			}
		}

		private CourierRequest GetClientData(string order)
		{
			Tuple<Destino, string> response = FetchClientData(company, order);
			if (response == null)
			{
				return null;
			}
			Dictionary<string, bool> opciones = new Dictionary<string, bool>();
			if (response.Item2.Length > 0)
			{
				opciones.Add("12", value: true);
			}
			CourierRequest courierReq = new CourierRequest
			{
				origen = new Origen
				{
					nombre = compName,
					direccion = compAddress,
					codigo_postal = compZip,
					localidad = compCity,
					pais = compCountry
				},
				destino = response.Item1,
				opciones = opciones,
				datos = new Datos
				{
					bultos = cantidadBultos,
					peso = Convert.ToDouble(pesoBulto * cantidadBultos)
				},
				referencia = order
			};
			if (courierReq.destino == null)
			{
				return null;
			}
			return courierReq;
		}

		private string PostSendingShipment(CourierRequest courierRequest)
		{
			string param1 = CreateMD5Hash(sendingPwd);
			string retorno = "N";
			if (courierRequest.opciones.Values.Count > 0)
			{
				retorno = "S";
			}
			string pais = "";
			if (courierRequest.destino.pais.ToString().Equals("ES"))
			{
				pais = "034";
			}
			else if (courierRequest.destino.pais.ToString().Equals("PT"))
			{
				pais = "035";
			}
			string fichero = string.Format("<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:web=\"http://webservices.sending.alerce.es/\">\n   <soapenv:Header/>\n <soapenv:Body>\n     <web:entrada_expediciones>\n        <cliente>{1}</cliente>\n        <fichero><![CDATA[<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>                             \n<Expediciones>\n<Expedicion>\n    <Fecha>{0}</Fecha>\n    <ClienteRemitente>{1}</ClienteRemitente>\n    <NombreRemitente>{2}</NombreRemitente>\n    <DireccionRemitente>{3}</DireccionRemitente>\n    <PaisRemitente>034</PaisRemitente>\n    <CodigoPostalRemitente>{4}</CodigoPostalRemitente>\n    <PoblacionRemitente>{5}</PoblacionRemitente>\n    <NombreDestinatario>{6}</NombreDestinatario>\n    <DireccionDestinatario>{7}</DireccionDestinatario>\n    <PaisDestinatario>{8}</PaisDestinatario>\n    <CodigoPostalDestinatario>{9}</CodigoPostalDestinatario>\n    <PoblacionDestinatario>{10}</PoblacionDestinatario>\n    <PersonaContactoDestinatario>{11}</PersonaContactoDestinatario>\n    <TelefonoContactoDestinatario>{12}</TelefonoContactoDestinatario>\n    <EnviarMail>N</EnviarMail>\n    <MailDestinatario>{13}</MailDestinatario>\n    <ProductoServicio>01</ProductoServicio>\n    <Observaciones1>{14}</Observaciones1>\n    <Kilos>{15}</Kilos>\n    <Volumen>0.00</Volumen>\n    <ReferenciaCliente>{14}</ReferenciaCliente>\n    <TipoPortes>P</TipoPortes>\n    <EntregaSabado>N</EntregaSabado>\n    <Retorno>{16}</Retorno>\n    <Bultos>{17}</Bultos>\n  </Expedicion>\n</Expediciones>\n]]>\n</fichero>\n       <formato>xml</formato>\n       <param1>{18}</param1>\n     </web:entrada_expediciones>\n  </soapenv:Body>\n</soapenv:Envelope>", DateTime.Now.ToString("dd/MM/yyyy"), sendingUser, "NATH GROUP", "C/ RIN 7 (AMPOSTA)", "08040", "BARCELONA", courierRequest.destino.nombre, courierRequest.destino.direccion, pais, courierRequest.destino.codigo_postal.Trim(), courierRequest.destino.localidad, courierRequest.destino.contacto.nombre, courierRequest.destino.contacto.telefono, courierRequest.destino.contacto.email, courierRequest.referencia.Replace("-", ""), Convert.ToDouble(courierRequest.datos.peso), retorno, courierRequest.datos.bultos.ToString(), param1);
			HttpWebRequest request = (HttpWebRequest)WebRequest.Create(sendingShipmentUrl);
			byte[] requestInFormOfBytes = Encoding.UTF8.GetBytes(fichero);
			request.Method = "POST";
			request.ContentType = "text/xml;charset=utf-8";
			request.ContentLength = requestInFormOfBytes.Length;
			using (Stream requestStream = request.GetRequestStream())
			{
				requestStream.Write(requestInFormOfBytes, 0, requestInFormOfBytes.Length);
			}
			HttpWebResponse obj = (HttpWebResponse)request.GetResponse();
			StreamReader streamReader = new StreamReader(obj.GetResponseStream());
			string receivedResponse = streamReader.ReadToEnd();
			streamReader.Close();
			obj.Close();
			XmlDocument xmlDocument = new XmlDocument();
			xmlDocument.LoadXml(receivedResponse);
			string trackingNum = xmlDocument.DocumentElement.InnerText.ToString();
			if (trackingNum.StartsWith("OK"))
			{
				return trackingNum.Replace("OK ", "");
			}
			return null;
		}

		private string GetSendingShipmentLabel(string referencia, string tracking, string sendingLabelPath)
		{
			try
			{
				string param1 = CreateMD5Hash(sendingPwd);
				string ficheroEtiqueta = $"<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:web=\"http://webservices.sending.alerce.es/\">\r\n   <soapenv:Header/>\r\n   <soapenv:Body>\r\n      <web:etiquetaPDF>\r\n         <cliente>{sendingUser}</cliente>\r\n         <expedicion>{tracking}</expedicion>\r\n         <param1>{param1}</param1>\r\n      </web:etiquetaPDF>\r\n   </soapenv:Body>\r\n</soapenv:Envelope>";
				HttpWebRequest requestEtiqueta = (HttpWebRequest)WebRequest.Create(sendingShipmentUrl);
				byte[] requestInFormOfBytesEtiqueta = Encoding.UTF8.GetBytes(ficheroEtiqueta);
				requestEtiqueta.Method = "POST";
				requestEtiqueta.ContentType = "text/xml;charset=utf-8";
				requestEtiqueta.ContentLength = requestInFormOfBytesEtiqueta.Length;
				using (Stream requestStream = requestEtiqueta.GetRequestStream())
				{
					requestStream.Write(requestInFormOfBytesEtiqueta, 0, requestInFormOfBytesEtiqueta.Length);
				}
				string response_reader = new StreamReader(((HttpWebResponse)requestEtiqueta.GetResponse()).GetResponseStream()).ReadToEnd();
				XmlDocument xmlDocument = new XmlDocument();
				xmlDocument.LoadXml(response_reader);
				string pdfContents = xmlDocument.DocumentElement.InnerText.ToString();
				string filename = company + "_" + referencia.Replace("/", "-") + ".pdf";
				string pdfFilename = Path.Combine(sendingLabelPath, filename);
				byte[] buffer = Convert.FromBase64String(pdfContents);
				using (Stream writer = File.Create(pdfFilename))
				{
					writer.Write(buffer, 0, buffer.Length);
					writer.Flush();
				}
				return pdfFilename;
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return null;
			}
		}

		private string CreateJsonString(CourierRequest courierReq)
		{
			string jsonString = "";
			try
			{
				string packText = "";
				if (courierReq.datos.bultos > 1)
				{
					for (int i = 0; i < courierReq.datos.bultos; i++)
					{
						packText += $"%s\n\"ancho\": \"\",\n\"observaciones\": \"\",\n\"kilos\": \"\",\n\"codBultoCli\": \"\",\n\"codUnico\": \"\",\n\"descripcion\": \"\",\n\"alto\": \"\",\n\"orden\": \"{i + 1}\",\n\"referencia\": \"\",\n\"volumen\": \"\",\n\"largo\": \"\"\n%d,\n";
					}
				}
				else
				{
					packText = $"%s\n\"ancho\": \"\",\n\"observaciones\": \"\",\n\"kilos\": \"\",\n\"codBultoCli\": \"\",\n\"codUnico\": \"\",\n\"descripcion\": \"\",\n\"alto\": \"\",\n\"orden\": \"{courierReq.datos.bultos}\",\n\"referencia\": \"\",\n\"volumen\": \"\",\n\"largo\": \"\"\n%d\n";
				}
				jsonString = string.Format("%s\"solicitante\": \"{0}\", \n\"canalEntrada\": \"\", \n\"numEnvio\": \"\", \n\"ref\": \"{1}\", \n\"refCliente\": \"{2}\", \n\"fecha\": \"{3}\", \n\"codRte\": \"{0}\", \n\"nomRte\": \"{4}\", \n\"nifRte\": \"\", \n\"dirRte\": \"{5}\", \n\"pobRte\": \"{6}\", \n\"codPosNacRte\": \"{7}\", \n\"paisISORte\": \"{8}\", \n\"codPosIntRte\": \"\", \n\"contacRte\": \"{9}\", \n\"telefRte\": \"{10}\", \n\"emailRte\": \"{11}\", \n\"codDest\": \"\", \n\"nomDest\": \"{12}\", \n\"nifDest\": \"\", \n\"dirDest\": \"{13}\", \n\"pobDest\": \"{14}\", \n\"codPosNacDest\": \"{15}\", \n\"paisISODest\": \"{16}\", \n\"codPosIntDest\": \"\", \n\"contacDest\": \"{17}\", \n\"telefDest\": \"{18}\", \n\"emailDest\": \"{19}\", \n\"contacOtrs\": \"\", \n\"telefOtrs\": \"\", \n\"emailOtrs\": \"\", \n\"observac\": \"\", \n\"numBultos\": \"{20}\", \n\"kilos\": \"{21}\", \n\"volumen\": \"\", \n\"alto\": \"\", \n\"largo\": \"\", \n\"ancho\": \"\", \n\"producto\": \"{22}\", \n\"portes\": \"{23}\", \n\"reembolso\": \"\", \n\"entrSabado\": \"\", \n\"seguro\": \"\", \n\"numEnvioVuelta\": \"\", \n\"listaBultos\": [{24}], \n\"codDirecDestino\": \"\", \n\"password\": \"\", \n\"listaInformacionAdicional\": [ \n%s\"tipoEtiqueta\": \"{25}\", \"etiquetaPDF\": \"\",\"codificacionUnicaB64\": \"1\" %d\n]\n%d", correosExpUserCode, courierReq.referencia.Replace("-", ""), courierReq.referencia.Replace("-", ""), DateTime.Now.ToString("ddMMyyyy"), compName, "C/ Rin 7", "Amposta", "43870", "ES", "Logistica NATH", "977707005", "logisticab2c@nath.es", courierReq.destino.nombre.Trim(), courierReq.destino.direccion.Trim(), courierReq.destino.localidad.Trim(), courierReq.destino.codigo_postal.Trim(), courierReq.destino.pais, courierReq.destino.contacto.nombre.Trim(), courierReq.destino.contacto.telefono.Trim(), courierReq.destino.contacto.email.Trim(), courierReq.datos.bultos.ToString(), Convert.ToDouble(courierReq.datos.peso).ToString(), "93", "P", packText, "1");
				jsonString = jsonString.Replace("%s", "{").Replace("%d", "}");
				Console.WriteLine(jsonString);
			}
			catch (Exception ex)
			{
				MessageBox.Show("CreateJsonString: " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand);
			}
			return jsonString;
		}

		private dynamic PostCexShipment(string url, string content, string username, string password)
		{
			object responseJson = null;
			try
			{
				byte[] jsonBytes = Encoding.UTF8.GetBytes(content);
				string encoded = Convert.ToBase64String(Encoding.GetEncoding("ISO-8859-1").GetBytes(username + ":" + password));
				HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
				request.Method = "POST";
				request.ContentType = "application/json";
				request.ContentLength = jsonBytes.Length;
				request.Headers.Add("Authorization", "Basic " + encoded);
				using (Stream requestStream = request.GetRequestStream())
				{
					requestStream.Write(jsonBytes, 0, jsonBytes.Length);
				}
				string response = string.Empty;
				using (StreamReader requestReader = new StreamReader(((HttpWebResponse)request.GetResponse()).GetResponseStream()))
				{
					response = requestReader.ReadToEnd();
				}
				responseJson = JsonConvert.DeserializeObject(response);
			}
			catch (Exception ex)
			{
				MessageBox.Show("PostCexShipment - " + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return responseJson;
		}

		private string GetCexShipmentLabel(string referencia, string jsonPdf, string correosExpLabelPath)
		{
			try
			{
				string filename = company + "_" + referencia.Replace("/", "-") + ".pdf";
				string pdfFilename = Path.Combine(correosExpLabelPath, filename);
				byte[] buffer = Convert.FromBase64String(jsonPdf);
				using (Stream writer = File.Create(pdfFilename))
				{
					writer.Write(buffer, 0, buffer.Length);
					writer.Flush();
				}
				return pdfFilename;
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return null;
			}
		}

		private string ReplaceAccents(string accentedStr)
		{
			byte[] tempBytes = Encoding.GetEncoding("ISO-8859-8").GetBytes(accentedStr);
			return Encoding.UTF8.GetString(tempBytes);
		}

		private string PostNacexShipment(CourierRequest courierRequest)
		{
			try
			{
				string email = string.Empty;
				email = ((courierRequest.destino.contacto.email.Length <= 0) ? nacexRecipPre1 : courierRequest.destino.contacto.email);
				string modPre = string.Empty;
				if (nacexTipPre1.Equals("E"))
				{
					modPre = "S";
				}
				string nombre_contacto = ReplaceAccents(courierRequest.destino.contacto.nombre);
				nombre_contacto = ((nombre_contacto.Length < 20) ? nombre_contacto.Trim() : nombre_contacto.Trim().Substring(0, 19));
				string dir_contacto = ReplaceAccents(courierRequest.destino.direccion);
				dir_contacto = ((dir_contacto.Length < 60) ? dir_contacto.Trim() : dir_contacto.Trim().Substring(0, 50));
				string localidad_contacto = ReplaceAccents(courierRequest.destino.localidad);
				string retorno = "N";
				if (courierRequest.opciones.Values.Count > 0)
				{
					retorno = "S";
				}
				string data = string.Format("del_cli={0}|num_cli={1}|tip_ser={2}|tip_cob={3}|ref_cli={4}|tip_env={5}|bul={6}|kil={7}|nom_ent={8}|dir_ent={9}|pais_ent={10}|cp_ent={11}|pob_ent={12}|tel_ent={13}|ret={19}|tip_pre1={14}|mod_pre1={15}|pre1={16}|obs1={4}|obs2={20}&user={17}&pass={18}", nacexAgency, nacexCustomerCode, nacexServiceCode, nacexCarriageCode, courierRequest.referencia.Replace("-", ""), nacexPackagingCode, courierRequest.datos.bultos.ToString(), Convert.ToDouble(courierRequest.datos.peso), nombre_contacto, dir_contacto, courierRequest.destino.pais, courierRequest.destino.codigo_postal.Trim(), localidad_contacto, courierRequest.destino.contacto.telefono, nacexTipPre1, modPre, email, nacexUsername, nacexPwd, retorno, courierRequest.destino.observaciones);
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create($"{nacexUrl}?method=putExpedicion&data={data}");
				obj.Method = "GET";
				obj.ContentType = "text/xml;charset=utf-8";
				HttpWebResponse obj2 = (HttpWebResponse)obj.GetResponse();
				StreamReader streamReader = new StreamReader(obj2.GetResponseStream());
				string receivedResponse = streamReader.ReadToEnd();
				streamReader.Close();
				obj2.Close();
				if (!receivedResponse.StartsWith("ERROR"))
				{
					return receivedResponse;
				}
				MessageBox.Show(receivedResponse, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return null;
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return null;
			}
		}

		private string GetNacexShipmentLabel(string referencia, string tracking, string nacexLabelPath)
		{
			try
			{
				string data = $"codExp={tracking}|modelo=PDF_B";
				string requestUriString = $"{nacexUrl}?method=getEtiqueta&data={data}|modelo=PDF_B&user={nacexUsername}&pass={nacexPwd}";
				_ = (HttpWebRequest)WebRequest.Create(requestUriString);
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(requestUriString);
				obj.Method = "GET";
				obj.ContentType = "text/html;charset=ISO-8859-1";
				string response_reader = new StreamReader(((HttpWebResponse)obj.GetResponse()).GetResponseStream()).ReadToEnd();
				if (response_reader.StartsWith("ERROR"))
				{
					MessageBox.Show(response_reader, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					return null;
				}
				string pdfContents = response_reader.Replace("\n", "").Replace(" ", "").Replace("*", "")
					.Replace('-', '+')
					.Replace('_', '/');
				int padding = pdfContents.Length % 4;
				if (padding != 0)
				{
					pdfContents += new string('=', 4 - padding);
				}
				byte[] buffer = Convert.FromBase64String(pdfContents);
				string filename = company + "_" + referencia.Replace("/", "-") + ".pdf";
				string pdfFilename = Path.Combine(nacexLabelPath, filename);
				using (Stream writer = File.Create(pdfFilename))
				{
					writer.Write(buffer, 0, buffer.Length);
					writer.Flush();
				}
				return pdfFilename;
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return null;
			}
		}

		public string GetEciDocuments(string eciOrderId)
		{
			HttpWebResponse response = null;
			try
			{
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(eciUrl, shopId, "&", eciOrderId, "&", eciDocType));
				obj.Method = "GET";
				obj.ContentType = "application/json";
				obj.Headers["Authorization"] = eciKey;
				response = (HttpWebResponse)obj.GetResponse();
				using (Stream stream = response.GetResponseStream())
				{
					using (StreamReader reader = new StreamReader(stream))
					{
						dynamic data = JsonConvert.DeserializeObject(reader.ReadToEnd());
						if ((data.total_count > 0) && (data.order_documents[0].type.ToString().Equals(eciDocType) ? true : false))
						{
							return data.order_documents[0].id;
						}
						return null;
					}
				}
			}
			catch (WebException ex)
			{
				ExceptionLogging.LogExceptionToFile(ex);
				if (ex.Status != WebExceptionStatus.ProtocolError && MessageBox.Show("Hubo un error de conexion al recuperar la etiqueta de ECI entrega en centro, volver a probar?", "Error de conexion", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					return GetEciDocuments(eciOrderId);
				}
				return null;
			}
			catch (Exception ex2)
			{
				ExceptionLogging.LogExceptionToFile(ex2);
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		public string GetEciLabel(string order, string eciDocId, string labelPath)
		{
			HttpWebResponse response = null;
			try
			{
				string referencia = order.Replace("/", "_");
				string labelFile = Path.Combine(labelPath, referencia + "-eci-" + eciDocId + ".pdf");
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(eciDocUrl, shopId, "&", eciDocId));
				obj.Method = "GET";
				obj.ContentType = "application/pdf";
				obj.Headers["Authorization"] = eciKey;
				response = (HttpWebResponse)obj.GetResponse();
				if (labelFile != null)
				{
					using (FileStream stream = File.Create(labelFile))
					{
						response.GetResponseStream().CopyTo(stream);
					}
				}
				return labelFile;
			}
			catch (WebException ex)
			{
				ExceptionLogging.LogExceptionToFile(ex);
				if (ex.Status != WebExceptionStatus.ProtocolError && MessageBox.Show("Hubo un error de conexion al recuperar la etiqueta de ECI entrega en centro, volver a probar?", "Error de conexion", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					return GetEciLabel(order, eciDocId, labelPath);
				}
				return null;
			}
			catch (Exception ex2)
			{
				ExceptionLogging.LogExceptionToFile(ex2);
				return null;
			}
			finally
			{
				response?.Close();
			}
		}
	}
}
