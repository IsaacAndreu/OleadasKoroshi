using System;
using System.IO;
using System.Net;
using System.Windows.Forms;
using CookComputing.XmlRpc;

namespace PedidosMultiples
{
	public class OdooClient
	{
		private readonly string url;

		private readonly string db;

		private readonly string username;

		private readonly string password;

		private int uid;

		public OdooClient(string url, string db, string username, string password)
		{
			this.url = url;
			this.db = db;
			this.username = username;
			this.password = password;
		}

		public int FetchOdooUid()
		{
			uid = 0;
			try
			{
				IOdooCommon common = XmlRpcProxyGen.Create<IOdooCommon>();
				common.Url = url + "/xmlrpc/2/common";
				uid = common.Authenticate(db, username, password, new XmlRpcStruct());
			}
			catch (WebException ex)
			{
				ExceptionLogging.LogExceptionToFile(ex);
				if (MessageBox.Show("Hubo un error de conexion en el login, volver a probar?", "Error de conexion", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					return FetchOdooUid();
				}
			}
			return uid;
		}

		public Tuple<int, string, string> CheckIfOperationExists(string operation, int company, int carrierIdIfNone, int packageTypeId)
		{
			int _pickingId = 0;
			string _origin = string.Empty;
			string pdfFilename = string.Empty;
			double _weight = 0.0;
			try
			{
				IOdooModels models = XmlRpcProxyGen.Create<IOdooModels>();
				models.Url = url + "/xmlrpc/2/object";
				object[] domain = new object[3]
				{
					new object[3] { "state", "=", "assigned" },
					new object[3] { "name", "=", operation },
					new object[3] { "company_id", "=", company }
				};
				XmlRpcStruct xmlRpcStruct = new XmlRpcStruct();
				xmlRpcStruct.Add("fields", new string[4] { "id", "origin", "carrier_id", "weight" });
				XmlRpcStruct fields = xmlRpcStruct;
				object[] operationData = (object[])models.ExecuteKw(db, uid, password, "stock.picking", "search_read", new object[1] { domain }, fields);
				if (operationData.Length == 0)
				{
					throw new Exception("Picking not found.");
				}
				XmlRpcStruct obj = (XmlRpcStruct)operationData[0];
				_pickingId = Convert.ToInt32(obj["id"]);
				_origin = obj["origin"].ToString();
				object carrierId = obj["carrier_id"];
				_weight = Convert.ToDouble(obj["weight"]);
				Console.WriteLine($"picking_id {_pickingId}, origin {_origin}, carrier_id {carrierId}");
				if (!_origin.StartsWith("ECI-") && !_origin.StartsWith("W") && !_origin.StartsWith("VP-") && !_origin.StartsWith("SRP-") && !_origin.StartsWith("VBD-") && !_origin.StartsWith("DS-"))
				{
					throw new Exception("Picking is not from Online channel.");
				}
				bool _updatedCarrier = false;
				if (carrierId != null && carrierId is object[] carrierArray && carrierArray.Length != 0)
				{
					XmlRpcStruct values = new XmlRpcStruct { { "carrier_id", false } };
					_updatedCarrier = Convert.ToBoolean(models.ExecuteKw(db, uid, password, "stock.picking", "write", new object[2]
					{
						new object[1] { _pickingId },
						values
					}));
					Console.WriteLine($"REMOVE CARRIER_ID _updated_carrier {_updatedCarrier}");
				}
				Console.WriteLine(models.ExecuteKw(db, uid, password, "stock.picking", "xml_put_in_pack", new object[1] { _pickingId }));
				if (_updatedCarrier && carrierId is object[] carrierArray2 && carrierArray2.Length != 0)
				{
					XmlRpcStruct values2 = new XmlRpcStruct
					{
						{
							"carrier_id",
							carrierArray2[0]
						},
						{ "number_of_packages", 1 }
					};
					_updatedCarrier = Convert.ToBoolean(models.ExecuteKw(db, uid, password, "stock.picking", "write", new object[2]
					{
						new object[1] { _pickingId },
						values2
					}));
					Console.WriteLine($"RESTORE ORIGINAL CARRIER_ID _updated_carrier {_updatedCarrier}");
				}
				else
				{
					XmlRpcStruct values3 = new XmlRpcStruct
					{
						{ "carrier_id", carrierIdIfNone },
						{ "number_of_packages", 1 }
					};
					_updatedCarrier = Convert.ToBoolean(models.ExecuteKw(db, uid, password, "stock.picking", "write", new object[2]
					{
						new object[1] { _pickingId },
						values3
					}));
					Console.WriteLine($"ADD PROGAMMED CARRIER_ID _updated_carrier {_updatedCarrier}");
				}
				if (packageTypeId > 0)
				{
					xmlRpcStruct = new XmlRpcStruct();
					xmlRpcStruct.Add("fields", new string[3] { "id", "origin", "package_ids" });
					XmlRpcStruct fieldsExtended = xmlRpcStruct;
					int[] packageIds = (int[])((XmlRpcStruct)((object[])models.ExecuteKw(db, uid, password, "stock.picking", "search_read", new object[1] { domain }, fieldsExtended))[0])["package_ids"];
					Console.WriteLine("package_ids " + string.Join(", ", packageIds));
					object[] packageSearchDomain = new object[2]
					{
						new object[3] { "id", "in", packageIds },
						new object[3] { "packaging_id", "=", false }
					};
					object[] packageIdsWithoutType = (object[])models.ExecuteKw(db, uid, password, "stock.quant.package", "search_read", new object[1] { packageSearchDomain });
					if (packageIdsWithoutType != null)
					{
						object[] packagesArray = packageIdsWithoutType;
						if (packagesArray.Length != 0)
						{
							int packageId = Convert.ToInt32(((XmlRpcStruct)packageIdsWithoutType[0])["id"]);
							XmlRpcStruct packagingValues = new XmlRpcStruct
							{
								{ "packaging_id", packageTypeId },
								{
									"shipping_weight",
									0.2 + _weight
								}
							};
							object updatedPackages = models.ExecuteKw(db, uid, password, "stock.quant.package", "write", new object[2]
							{
								new object[1] { packageId },
								packagingValues
							});
							Console.WriteLine($"updated packages {updatedPackages}");
							if (Convert.ToBoolean(updatedPackages))
							{
								object pickingValidate = models.ExecuteKw(db, uid, password, "stock.picking", "action_done", new object[1] { new object[1] { _pickingId } });
								Console.WriteLine($"validate picking {pickingValidate}");
								if (!(Convert.ToBoolean(pickingValidate) && _updatedCarrier))
								{
									throw new Exception("Picking not validated or carrier not assigned.");
								}
								if ((carrierId is object[] carrierArray3 && carrierArray3.Length != 0 && Convert.ToInt32(carrierArray3[0]) == 298) || carrierIdIfNone == 298)
								{
									models.ExecuteKw(db, uid, password, "stock.picking", "xml_send_to_shipper", new object[1] { _pickingId });
								}
								object[] documentDomain = new object[2]
								{
									new object[3] { "res_model", "=", "stock.picking" },
									new object[3] { "res_id", "=", _pickingId }
								};
								xmlRpcStruct = new XmlRpcStruct();
								xmlRpcStruct.Add("fields", new string[3] { "id", "datas", "name" });
								XmlRpcStruct documentFields = xmlRpcStruct;
								object[] pickingAttachments = (object[])models.ExecuteKw(db, uid, password, "ir.attachment", "search_read", new object[1] { documentDomain }, documentFields);
								if (pickingAttachments != null)
								{
									object[] attachmentArray = pickingAttachments;
									if (attachmentArray.Length != 0)
									{
										string encodedPdf = string.Empty;
										string fileName = string.Empty;
										object[] array = attachmentArray;
										for (int i = 0; i < array.Length; i++)
										{
											XmlRpcStruct docData = (XmlRpcStruct)array[i];
											if (docData["name"].ToString().ToLower().Contains("label") || docData["name"].ToString().ToLower().Contains("seur"))
											{
												encodedPdf = docData["datas"].ToString();
												fileName = string.Format("{0} {1}", operation.Replace("/", "_"), docData["name"].ToString().Replace("/", "_").Replace(" ", "_"));
											}
										}
										if (!fileName.Equals(string.Empty))
										{
											pdfFilename = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "Labels", fileName);
											byte[] buffer = Convert.FromBase64String(encodedPdf);
											using (Stream writer = File.Create(pdfFilename))
											{
												writer.Write(buffer, 0, buffer.Length);
												writer.Flush();
											}
										}
									}
								}
							}
						}
					}
				}
			}
			catch (Exception ex)
			{
				ExceptionLogging.LogExceptionToFile(ex);
				_pickingId = 0;
				_origin = string.Empty;
				MessageBox.Show("Validar " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return new Tuple<int, string, string>(_pickingId, _origin, pdfFilename);
		}
	}
}
