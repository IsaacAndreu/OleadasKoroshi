using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Configuration;
using System.Data;
using System.Data.SqlClient;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Printing;
using System.IO;
using System.Linq;
using System.Media;
using System.Net;
using System.Net.Mail;
using System.Speech.Synthesis;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using AutoUpdaterDotNET;
using BarcodeLib;
using CookComputing.XmlRpc;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Npgsql;
using PdfiumViewer;
using PedidosMultiples.Properties;
using iTextSharp.text;
using iTextSharp.text.pdf;
using iTextSharp.text.pdf.draw;

namespace PedidosMultiples
{
	public class InitialForm : Form
	{
		private static SoundPlayer sound_ok = null;

		private static SoundPlayer sound_error = null;

		private static SoundPlayer sound_alert = null;

		private static SoundPlayer sound_final = null;

		private static SoundPlayer sound_eci = null;

		private int db;

		private string company;

		private const string NATH = "NATH";

		private const string ALAN = "ALAN";

		private const string CODE = "CODE";

		private const string TCN = "TCN";

		private const string TTUC = "TTUC";

		private const string EFFE = "EFFE";

		private Dictionary<string, int> companyIds = new Dictionary<string, int>();

		private DataTable dataTableSource = new DataTable();

		private DataTable packingListDt = new DataTable();

		private SpeechSynthesizer synth = new SpeechSynthesizer();

		private string textBoxInput = "";

		private bool acceptPe = true;

		private string lastValidProduct = "";

		private string cellSequenceValue = "";

		private string lastPE = "";

		private int rowOnDoubleClick;

		private bool sendEmails;

		private bool buttonClicked;

		private bool printPacking = true;

		private bool printLabels = true;

		private bool ECImode;

		private bool VPmode;

		private bool cambiarCaja;

		private bool modoPrueba;

		private bool modoMatricula;

		// Modo matricula: la matricula la genera Odoo al cerrar la caja (sin preregistro ni lectura)
		private bool matriculaAuto;

		private const string PrefijoMatricula = "CJ";

		private OdooAccion odooAccion;

		private int accionEmpaquetarId;

		// Modo matricula: matriculas pendientes por SEQ, en orden de uso (la primera es la de la caja abierta).
		private Dictionary<string, List<string>> matriculasPorSeq = new Dictionary<string, List<string>>();

		private HashSet<string> matriculasUsadas = new HashSet<string>();

		private bool MatriculaActiva => modoMatricula && company == "EFFE" && !ECImode && !VPmode;

		private string queryInicial = "select sml.reference as PE, pt.style_code as Style, COALESCE(color.name, '27 UNICO') as COLOR, COALESCE(talla.name, '') as SIZE, pp.default_code as Product_Code, COALESCE(pp.barcode, '') as EAN_Code, CASE    WHEN sml.product_uom_qty = 0 AND sml.state = 'done' THEN sml.qty_done    ELSE sml.product_uom_qty END AS QTY, sml.qty_done as Leido, sml.id as sml_id, (select trim(so.ref_remarks) from sale_order so where so.id = (select sp.sale_id from stock_picking sp where sp.name = (@order))) as LI_Intitule, pp.x_studio_veepee_product_id as veepee_product_id, 'parcel_id' as LI_Complement, 'pallet_id' as LI_Pallet from stock_move_line sml left join product_product pp on pp.id = sml.product_id left join product_template pt on pt.id = pp.product_tmpl_id left join (select ptav.id, pav.name from product_template_attribute_value ptav, product_attribute_value pav where ptav.product_attribute_value_id = pav.id) as talla on pp.size_attribute_id = talla.id left join(select ptav.id, pav.name from product_template_attribute_value ptav, product_attribute_value pav where ptav.product_attribute_value_id = pav.id) as color on pp.color_attribute_id = color.id where sml.company_id = (@company_id) and (sml.reference = (@order) and sml.picking_id = (select id from stock_picking sp where sp.name = (@order))) and (select state from stock_picking where name = (@order)) in ('assigned', 'done') order by pt.style_code;";

		private string queryCheckIfOrderStateIsAssigned = "select sp.name, sp.state from stock_picking sp where sp.name = (@order) and sp.state = 'assigned' and company_id = (@company_id);";

		private string queryPeDateLivr = "SELECT TOP(1) DO_DateLivr FROM F_DOCENTETE WHERE DO_PIECE = @input;";

		private string queryPeDoDate = "SELECT TOP(1) DO_Date FROM F_DOCENTETE WHERE DO_PIECE = @input;";

		private string queryGetClientData = "select entrega.name as Name, entrega.street as Address, entrega.street2 as Complement, entrega.zip as CodePostal, entrega.city as Ville, entrega.province as CodeRegion, entrega.country as Pays, entrega.phone_sanitized as Telephone, entrega.email_normalized as Email, sp.scheduled_date as DeliveryDate, entrega.province_code as province_code, entrega.country_code as country_code, sp.note, sp.origin, sp.x_studio_order_remarks as remarks, mirakl.shipping_type_label as shipping_type_label from stock_picking sp join res_company rc on rc.id = sp.company_id join(   select rp.id, rp.name, rp.contact_address_complete, rp.street, rp.street2, rp.zip, rp.city,    rcs2.name as province,    rcs2.code as province_code,    rc.name as country,    rc.code as country_code,    rp.email_normalized, rp.phone_sanitized, rp.old_code as cod_sage    from res_partner rp    left join res_country rc on rc.id = rp.country_id    left join res_country_state rcs2 on rcs2.id = rp.state_id    ) as entrega on entrega.id = sp.partner_id left join(    select so.id as pedido, so.mirakl_mapping_id, mof.shipping_type_label    from sale_order so    left join mirakl_order_mapping mom on mom.id = so.mirakl_mapping_id    left join mirakl_order_feed mof on mof.id = mom.odoo_feed ) as mirakl on mirakl.pedido = sp.sale_id where sp.name = (@order) and sp.company_id = (@company_id);";

		private string queryGetLocationBarcode = "select sp.name, sp.origin, sl.barcode from stock_picking sp join res_company rc on rc.id = sp.company_id join stock_location sl on sl.id = sp.location_dest_id where sl.barcode is not null and sp.origin = (select origin from stock_picking where name = (@order)) and sp.company_id = (@company_id) limit 1;";

		private string queryUpdateStockMoveLine = "update stock_move_line set qty_done = @qty, write_date = NOW()::timestamp where id = (@id) and reference = (@order) and product_id = (select id from product_product pp where pp.barcode = (@ean_code)) and company_id = (@company_id) and (select state from stock_picking where name = (@order)) = 'assigned';";

		private string queryGetSumStockMoveLines = "select sum(sml.qty_done) as qty_done from stock_move_line sml where sml.reference = (@order) and sml.company_id = (@company_id) and (select state from stock_picking where name = (@order)) = 'assigned';";

		private string crmConectionString = "Persist Security Info=False;Initial Catalog=ALMACENTOSSES;Data Source=192.168.0.3;User ID=nathit;Password=St39em87";

		private string insertOrderPrintLogCrmQuery = "INSERT INTO OrderPrintLog (OrderId, ComapnyName, CompanyOrderId, PrintTime) VALUES (@orderId, @companyName, @companyOrderId, GETDATE());";

		private string insertOrderDoubleCheckingLogQuery = "INSERT INTO OrderDoubleCheckingLog (OrderId, ComapnyName, CompanyOrderId, Time, Revisor, Status) VALUES (@orderId, @companyName, @companyOrderId, GETDATE(), 'PM', 'done');";

		private string queryInsertProductivityRecords = "INSERT INTO Productividad_Operadores (user_id, articulos_jornada, duracion_jornada, duracion_pausas, estacion_trabajo, fecha_creacion) VALUES (@user_id, @articulos_jornada, @duracion_jornada, @duracion_pausas, @estacion_trabajo, GETDATE());";

		private string queryGetOrdersByBatchName = "select sp.name as operation from stock_picking sp left join stock_picking_batch spb on spb.id = sp.batch_id where spb.name = (@batch_name) and sp.state in ('assigned', 'done') and spb.state = 'in_progress'and spb.company_id = (@company_id) and spb.company_id = sp.company_id ORDER BY sp.name ASC;";

		private double articlesTotal;

		private double articlesLeido;

		private double leidoPercent;

		private double articleManual;

		private double shiftArticles;

		private double productivity;

		private double shiftProductivity;

		private const int productivityThreshold = 100;

		private System.Windows.Forms.Timer _timer;

		private System.Windows.Forms.Timer _shiftTimer;

		private System.Windows.Forms.Timer _shiftPauseTimer;

		private DateTime _startTime = DateTime.MinValue;

		private TimeSpan _currentElapsedTime = TimeSpan.Zero;

		private TimeSpan _totalElapsedTime = TimeSpan.Zero;

		private DateTime _shiftStartTime = DateTime.MinValue;

		private TimeSpan _shiftCurrentElapsedTime = TimeSpan.Zero;

		private TimeSpan _shiftTotalTime = TimeSpan.Zero;

		private DateTime _shiftPauseStartTime = DateTime.MinValue;

		private TimeSpan _shiftCurrentPausedTime = TimeSpan.Zero;

		private TimeSpan _shiftTotalPausedTime = TimeSpan.Zero;

		private bool _timerRunning;

		private bool _shiftTimerRunning;

		private bool _shiftPauseTimerRunning;

		private List<string> peListMultiple = new List<string>();

		private HashSet<string> peList = new HashSet<string>();

		private string nombreOleada;

		private char[] chars_to_replace = new char[9] { '/', '\\', ':', '*', '?', '"', '<', '>', '|' };

		private int seqLength = 3;

		private static bool crmLogs;

		private string publicIp;

		private string appPath = string.Empty;

		private string pdfPath = string.Empty;

		private string logFolderPath = string.Empty;

		private string pdfPackingPath = string.Empty;

		private string labelPath = string.Empty;

		private const int COPIES = 1;

		private const string LABEL_SIZE = "A6";

		private const string PAPER_SIZE = "A4";

		private Dictionary<string, string> userDict = new Dictionary<string, string>();

		private string token;

		private string base_url;

		private string api_version;

		private string warehouse_id;

		private bool generateShipmentLabels;

		private Envios envios;

		private Origen origen;

		private Destino destino;

		private Datos datos;

		private string referencia;

		private Dictionary<string, bool> opciones;

		private string defaultPdfLabel;

		private string eciPdfLabel;

		private static Regex _gtinRegex = new Regex("^(\\d{8}|\\d{12,14})$");

		private IContainer components;

		private MenuStrip menuStrip1;

		private ToolStripMenuItem baseDeDatosToolStripMenuItem;

		private ToolStripMenuItem nATH1ToolStripMenuItem;

		private ToolStripMenuItem aLANToolStripMenuItem;

		private ToolStripMenuItem codeToolStripMenuItem;

		private ToolStripMenuItem tCNToolStripMenuItem;

		private StatusStrip statusStrip1;

		private ToolStripStatusLabel toolStripStatusLabel1;

		private ToolStripStatusLabel toolStripStatusLabel2;

		private Panel panelScanPe;

		private TextBox scanInput;

		private Label lblPe;

		private Button nextBtn;

		private Panel panelTable;

		private DataGridView articlesGrid;

		private ToolStripStatusLabel serverIpLbl;

		private ToolStripStatusLabel databaseNameLbl;

		private Panel progressBarTotal;

		private ToolStripMenuItem históricoToolStripMenuItem;

		private ToolStripMenuItem NathRecuperar;

		private ToolStripMenuItem AlanRecuperar;

		private ToolStripMenuItem CodeRecuperar;

		private ToolStripMenuItem TcnRecuperar;

		private TextBox newBoxTxt;

		private Button nextBoxBtn;

		private ToolStripMenuItem opcionesToolStripMenuItem;

		private ToolStripMenuItem enviarEmailsToolStripMenuItem;

		private Label seqValueLbl;

		private Button pendingArticlesBtn;

		private Label _totalElapsedTimeDisplay;

		private Button pauseTimerBtn;

		private Button productivityBtn;

		private Label totalUnitsHourLbl;

		private Button filtroPendBtn;

		private Label timeRemainingLbl;

		private TextBox nombreOleadaTxt;

		private Label nombreOleadaLbl;

		private TextBox pendientesPedidoBox;

		private Label pendientesPedidoLabel;

		private ToolStripMenuItem imprimirPackingToolStripMenuItem;

		private ToolStripMenuItem modoECIToolStripMenuItem;

		private ToolStripStatusLabel modeStatusLabel;

		private ToolStripMenuItem configuraciónToolStripMenuItem;

		private TextBox pklNoAcabadoTxt;

		private Label label1;

		private ToolStripStatusLabel VersionLabel;

		private TextBox pklTemporalTxt;

		private Label label2;

		private ToolStripMenuItem tUCTUCToolStripMenuItem;

		private ToolStripMenuItem TtucRecuperar;

		private Label shiftProductivityLabel;

		private Label shiftScansLabel;

		private Label _shiftPausedTimeDisplay;

		private Label _shiftTotalTimeDisplay;

		private ToolTip toolTip1;

		private Label label3;

		private TextBox boxLblPrintTxt;

		private ToolStripMenuItem buscarActualizacionesToolStripMenuItem;

		private ToolStripMenuItem imprimirEtiquetasCajaToolStripMenuItem;

		private ToolStripMenuItem modoVPToolStripMenuItem;

		private Button assignPaletBtn;

		private GroupBox modoVPGroupBox;

		private Label label4;

		private TextBox rePrintVpLabelBox;

		private TextBox palletNumBox;

		private ToolStripMenuItem generarEtiquetasEnvioToolStripMenuItem;

		private ToolStripMenuItem eFFECTIVEToolStripMenuItem;

		private ToolStripMenuItem EffectiveRecuperar;

		public static void SetCrmLogs(bool value)
		{
			crmLogs = value;
		}

		public InitialForm()
		{
			InitializeComponent();
			VersionLabel.Text = Application.ProductVersion;
			appPath = Path.GetDirectoryName(Application.ExecutablePath);
			pdfPath = Path.Combine(appPath, "Pendientes");
			if (!Directory.Exists(pdfPath))
			{
				Directory.CreateDirectory(pdfPath);
			}
			logFolderPath = Path.Combine(appPath, "Logs");
			if (!Directory.Exists(logFolderPath))
			{
				Directory.CreateDirectory(logFolderPath);
			}
			pdfPackingPath = Path.Combine(appPath, "Packing List");
			if (!Directory.Exists(pdfPackingPath))
			{
				Directory.CreateDirectory(pdfPackingPath);
			}
			labelPath = Path.Combine(appPath, "Labels");
			if (!Directory.Exists(labelPath))
			{
				Directory.CreateDirectory(labelPath);
			}
			defaultPdfLabel = Path.Combine(appPath, "expediciones_label.pdf");
			eciPdfLabel = Path.Combine(appPath, "eci_label.pdf");
			_timer = new System.Windows.Forms.Timer
			{
				Interval = 1000
			};
			_timer.Tick += _timer_Tick;
			_shiftTimer = new System.Windows.Forms.Timer
			{
				Interval = 1000
			};
			_shiftTimer.Tick += _timer_Tick;
			_shiftPauseTimer = new System.Windows.Forms.Timer
			{
				Interval = 1000
			};
			_shiftPauseTimer.Tick += _pause_timer_Tick;
			try
			{
				if (sound_ok == null)
				{
					sound_ok = new SoundPlayer(Resources.correct);
					sound_ok.LoadAsync();
					sound_error = new SoundPlayer(Resources.error);
					sound_error.LoadAsync();
					sound_alert = new SoundPlayer(Resources.alert);
					sound_alert.LoadAsync();
					sound_final = new SoundPlayer(Resources.finalizar);
					sound_final.LoadAsync();
					sound_eci = new SoundPlayer(Resources.alert_simple);
					sound_eci.LoadAsync();
				}
			}
			catch (Exception ex)
			{
				ex.ToString();
			}
		}

		private void Form1_Load(object sender, EventArgs e)
		{
			companyIds.Add("NATH", 1);
			companyIds.Add("ALAN", 23);
			companyIds.Add("CAREY", 11);
			companyIds.Add("CODE", 21);
			companyIds.Add("TCN", 2);
			companyIds.Add("TTUC", 1);
			companyIds.Add("TTUC_CAD", 3);
			companyIds.Add("TTUC_USA", 4);
			companyIds.Add("TTUC_COP", 5);
			companyIds.Add("EFFE", 8);
			panelScanPe.Visible = false;
			panelTable.Visible = false;
			progressBarTotal.Visible = false;
			pendientesPedidoBox.Enabled = false;
			pklNoAcabadoTxt.Enabled = false;
			panelScanPe.Controls.Add(lblPe);
			nextBtn.Enabled = false;
			nextBoxBtn.Enabled = false;
			filtroPendBtn.Enabled = false;
			pendingArticlesBtn.Enabled = false;
			pauseTimerBtn.Enabled = false;
			boxLblPrintTxt.Enabled = false;
			modoVPGroupBox.Visible = false;
			CheckOrUncheckOptionMenu("enviar", enviarEmailsToolStripMenuItem, sendEmails);
			CheckOrUncheckOptionMenu("imprimirPacking", imprimirPackingToolStripMenuItem, printPacking);
			CheckOrUncheckOptionMenu("imprimirLabels", imprimirEtiquetasCajaToolStripMenuItem, printLabels);
			packingListDt.Columns.Add("BOX", typeof(int));
			packingListDt.Columns.Add("STYLE", typeof(string));
			packingListDt.Columns.Add("COLOR", typeof(string));
			packingListDt.Columns.Add("SIZE", typeof(string));
			packingListDt.Columns.Add("EAN", typeof(string));
			packingListDt.Columns.Add("QTY", typeof(int));
			packingListDt.Columns.Add("PE", typeof(string));
			nombreOleada = "";
			AddUpdateAppSettings("modoECI", "false");
			AddUpdateAppSettings("modoVP", "false");
			crmLogs = Convert.ToBoolean(ReturnSetting("crm_logs"));
			publicIp = ReturnSetting("public_ip");
			synth.SetOutputToDefaultAudioDevice();
			userDict.Add("userName", ReturnSetting("user"));
			userDict.Add("password", ReturnSetting("password"));
			base_url = ReturnSetting("base_url");
			api_version = ReturnSetting("api_version");
			warehouse_id = ReturnSetting("warehouse_id");
			envios = new Envios();
			AddUpdateAppSettings("generarEtiquetas", "false");
			modoPrueba = (ReturnSetting("koroshi_modo_prueba") ?? "").Equals("true", StringComparison.OrdinalIgnoreCase);
			if (modoPrueba)
			{
				crmLogs = false;
				Text += " - MODO PRUEBA (no escribe en Odoo ni en SQL Server)";
				LogPrueba("Inicio del programa en modo prueba");
			}
			modoMatricula = (ReturnSetting("koroshi_modo_matricula") ?? "").Equals("true", StringComparison.OrdinalIgnoreCase);
			if (modoMatricula)
			{
				odooAccion = OdooAccion.DesdeConfiguracion();
				int.TryParse(ReturnSetting("odoo_accion_empaquetar_id"), out accionEmpaquetarId);
				matriculaAuto = !(ReturnSetting("koroshi_matricula_auto") ?? "").Equals("false", StringComparison.OrdinalIgnoreCase);
			}
			opcionesToolStripMenuItem.DropDownItems.Add("Imprimir etiqueta de caja de prueba", null, imprimirEtiquetaPrueba_Click);
		}

		private void resetFormOnDbChange()
		{
			panelScanPe.Visible = true;
			panelTable.Visible = true;
			progressBarTotal.Visible = true;
			lblPe.Text = "ESCANEAR PEDIDOS - \n" + company;
			lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
			panelScanPe.BackColor = default(Color);
			scanInput.Text = null;
			scanInput.Select();
			acceptPe = true;
			articlesTotal = 0.0;
			articlesLeido = 0.0;
			articleManual = 0.0;
			shiftArticles = 0.0;
			articlesGrid.DataSource = null;
			dataTableSource.Clear();
			articlesGrid.Rows.Clear();
			articlesGrid.Refresh();
			databaseNameLbl.Text = company + " " + db;
			seqValueLbl.Text = "";
			filtroPendBtn.Enabled = false;
			pendingArticlesBtn.Enabled = false;
			productivityBtn.Enabled = false;
			pauseTimerBtn.Enabled = false;
			pendientesPedidoBox.Enabled = false;
			pklNoAcabadoTxt.Enabled = false;
			pklTemporalTxt.Enabled = false;
			boxLblPrintTxt.Enabled = false;
			if (!VPmode)
			{
				modoVPGroupBox.Visible = false;
			}
			productivity = 0.0;
			totalUnitsHourLbl.Text = "Ritmo (U/h): ";
			shiftScansLabel.Text = "Unidades (turno): 0";
			shiftProductivityLabel.Text = "U/h (turno): 0";
			UpdateProgressBar();
			resetTimer();
			peList.Clear();
			packingListDt.Rows.Clear();
			nombreOleada = "";
			nombreOleadaTxt.Enabled = true;
			nombreOleadaLbl.Text = "Nombre oleada: *";
			matriculasPorSeq.Clear();
			matriculasUsadas.Clear();
		}

		private void SetCompanyVariables(string companyName)
		{
			company = companyName;
			db = companyIds[companyName];
			envios.SetCompanyVariablesEnvios(companyName, db);
		}

		private void aLANToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				SetCompanyVariables("ALAN");
				UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
				resetFormOnDbChange();
			}
			catch (NpgsqlException ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void nATH1ToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				SetCompanyVariables("NATH");
				UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
				resetFormOnDbChange();
			}
			catch (NpgsqlException ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void codeToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				SetCompanyVariables("CODE");
				UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
				resetFormOnDbChange();
			}
			catch (NpgsqlException ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void tCNToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				SetCompanyVariables("TCN");
				UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
				resetFormOnDbChange();
			}
			catch (NpgsqlException ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void tUCTUCToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				SetCompanyVariables("TTUC");
				UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
				resetFormOnDbChange();
			}
			catch (NpgsqlException ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void eFFECTIVEToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				SetCompanyVariables("EFFE");
				UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
				resetFormOnDbChange();
			}
			catch (NpgsqlException ex)
			{
				MessageBox.Show(ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void buildTable(string entrada)
		{
			try
			{
				string lastRowValue = "";
				int boxToAssign = 1;
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand obj = new NpgsqlCommand(queryInicial, cSql.dbConn)
					{
						CommandTimeout = 120
					};
					if (company.Equals("TTUC"))
					{
						if (entrada.StartsWith("W_CAD"))
						{
							db = companyIds["TTUC_CAD"];
						}
						else if (entrada.StartsWith("W_COP"))
						{
							db = companyIds["TTUC_COP"];
						}
						else if (entrada.StartsWith("W_USA"))
						{
							db = companyIds["TTUC_USA"];
						}
					}
					if (company.Equals("ALAN") && entrada.StartsWith("CAREY"))
					{
						db = companyIds["CAREY"];
					}
					obj.Parameters.AddWithValue("@company_id", db);
					obj.Parameters.AddWithValue("@order", entrada);
					using (NpgsqlDataAdapter adapter = new NpgsqlDataAdapter(obj))
					{
						adapter.Fill(dataTableSource);
					}
					if (dataTableSource.Columns.Count > 0 && dataTableSource.Rows.Count > 0)
					{
						if (!dataTableSource.Columns.Contains("veepee_ref"))
						{
							dataTableSource.Columns.Add("veepee_ref", typeof(string));
						}
						if (!dataTableSource.Columns.Contains("SEQ"))
						{
							dataTableSource.Columns.Add("SEQ", typeof(string));
						}
						if (!dataTableSource.Columns.Contains("Caja"))
						{
							dataTableSource.Columns.Add("Caja", typeof(int));
						}
						if (!dataTableSource.Columns.Contains("Finalizado"))
						{
							dataTableSource.Columns.Add("Finalizado", typeof(bool));
						}
					}
					for (int i = 0; i < dataTableSource.Rows.Count; i++)
					{
						lastRowValue = ((i != 0) ? dataTableSource.Rows[i - 1]["PE"].ToString() : dataTableSource.Rows[i]["PE"].ToString());
						if (dataTableSource.Rows[i]["PE"].ToString().Equals(lastRowValue))
						{
							dataTableSource.Rows[i]["SEQ"] = boxToAssign.ToString("D" + seqLength);
							seqValueLbl.Text = boxToAssign.ToString("D" + seqLength);
						}
						else
						{
							boxToAssign++;
							dataTableSource.Rows[i]["SEQ"] = boxToAssign.ToString("D" + seqLength);
							seqValueLbl.Text = boxToAssign.ToString("D" + seqLength);
						}
						dataTableSource.Rows[i]["Caja"] = 1;
						dataTableSource.Rows[i]["Finalizado"] = false;
						if (dataTableSource.Rows[i]["LI_Intitule"].ToString().Contains("#") && dataTableSource.Rows[i]["LI_Intitule"].ToString().Contains("TTUC"))
						{
							dataTableSource.Rows[i]["veepee_ref"] = dataTableSource.Rows[i]["LI_Intitule"].ToString().Split('#')[3];
						}
					}
					articlesGrid.DataSource = dataTableSource;
					if (dataTableSource.Columns.Count > 0 && dataTableSource.Rows.Count > 0 && articlesGrid.Columns.Count > 0 && articlesGrid.Rows.Count > 0)
					{
						if (articlesGrid.Columns.Contains("sml_id"))
						{
							articlesGrid.Columns["sml_id"].Visible = false;
						}
						if (articlesGrid.Columns.Contains("li_intitule"))
						{
							articlesGrid.Columns["li_intitule"].Visible = false;
						}
						if (articlesGrid.Columns.Contains("veepee_product_id"))
						{
							articlesGrid.Columns["veepee_product_id"].Visible = false;
						}
						if (articlesGrid.Columns.Contains("LI_Complement"))
						{
							articlesGrid.Columns["LI_Complement"].Visible = false;
						}
						if (articlesGrid.Columns.Contains("LI_Pallet"))
						{
							articlesGrid.Columns["LI_Pallet"].Visible = true;
						}
						if (!VPmode && articlesGrid.Columns.Contains("veepee_ref"))
						{
							articlesGrid.Columns["veepee_ref"].Visible = false;
						}
						nextBtn.Enabled = true;
					}
				}
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("funcion buildTable_ Hubo un error! \n" + ex, "Error " + entrada, MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					buildTable(entrada);
				}
			}
		}

		private List<string> GetOrdersByBatchName(string scannedInput)
		{
			List<string> orders = new List<string>();
			try
			{
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryGetOrdersByBatchName, cSql.dbConn);
					npgsqlCommand.Parameters.AddWithValue("@batch_name", scannedInput);
					if (company.Equals("TTUC"))
					{
						if (scannedInput.StartsWith("W_CAD"))
						{
							db = companyIds["TTUC_CAD"];
						}
						else if (scannedInput.StartsWith("W_COP"))
						{
							db = companyIds["TTUC_COP"];
						}
						else if (scannedInput.StartsWith("W_USA"))
						{
							db = companyIds["TTUC_USA"];
						}
					}
					if (company.Equals("ALAN") && scannedInput.StartsWith("CAREY"))
					{
						db = companyIds["CAREY"];
					}
					npgsqlCommand.Parameters.AddWithValue("@company_id", db);
					NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
					if (reader.HasRows)
					{
						while (reader.Read())
						{
							orders.Add(reader["operation"].ToString());
						}
						reader.Close();
					}
					cSql.dbConn.Close();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("GetOrdersByBatchName " + ex.Message, "Error " + scannedInput, MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return orders;
		}

		private void scanInput_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
			}
			else if (e.KeyCode == Keys.Return)
			{
				if (nombreOleada == null || nombreOleada == "")
				{
					MessageBox.Show("Falta introducir el nombre de la oleada", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					scanInput.Clear();
				}
				else
				{
					e.SuppressKeyPress = true;
					textBoxInput = scanInput.Text.Trim();
					flow(textBoxInput);
				}
			}
		}

		private void flow(string input)
		{
			if (input == "MATRICULAS" && MatriculaActiva && !matriculaAuto)
			{
				scanInput.Text = "";
				AbrirMatriculas();
			}
			else if (input == "CAMBIAR-CAJA")
			{
				if (articlesGrid.Rows.Count > 0 && peList.Count > 1)
				{
					cambiarCaja = true;
					lblPe.Text = "CAMBIAR CAJA";
				}
				else if (peList.Count == 1)
				{
					changeBox(articlesGrid.Rows[0].Cells["SEQ"].Value.ToString(), increment: true);
				}
				scanInput.Text = "";
				scanInput.Select();
			}
			else if (ECImode && !cambiarCaja)
			{
				processScannedInputECI(input);
			}
			else if (!ECImode && !cambiarCaja)
			{
				processScannedInput(input);
			}
			else if (cambiarCaja)
			{
				changeBox(input, increment: true);
				cambiarCaja = false;
			}
		}

		private void processScannedInput(string textBoxInput)
		{
			try
			{
				bool foundInTable = false;
				bool foundBox = false;
				if ((textBoxInput.Contains("/OUT/") || textBoxInput.Contains("/INT/")) && textBoxInput.Contains(";") && acceptPe)
				{
					string[] source = textBoxInput.Split(';');
					List<string> noDupes = source.Distinct().ToList();
					IEnumerable<string> duplicates = (from result in source
						group result by result).SelectMany((IGrouping<string, string> grp) => grp.Skip(1).Take(1));
					if (duplicates.Count() > 0)
					{
						string message = string.Empty;
						foreach (string item in duplicates)
						{
							message = message + item + "\n";
						}
						MessageBox.Show(message, "Pedidos duplicados", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
					foreach (string peCode in noDupes)
					{
						if ((peCode.Contains("/OUT/") || peCode.Contains("/INT")) && isValidCode(peCode))
						{
							peList.Add(peCode.ToString());
						}
					}
					foreach (string item2 in peList)
					{
						buildTable(item2.ToString());
					}
					sound_ok.Play();
					if (crmLogs)
					{
						InsertRecordsIntoCrmDatabase(peList);
					}
					NextBtnClickAction();
				}
				else if (acceptPe && (textBoxInput.StartsWith("B-") || textBoxInput.StartsWith("BATCH/") || textBoxInput.StartsWith("ECI_") || textBoxInput.StartsWith("VP_") || textBoxInput.StartsWith("WEB_")))
				{
					List<string> noDupes2 = GetOrdersByBatchName(textBoxInput.ToString());
					if (noDupes2.Count > 0)
					{
						foreach (string item3 in noDupes2)
						{
							buildTable(item3.ToString());
						}
						sound_ok.Play();
						if (crmLogs)
						{
							InsertRecordsIntoCrmDatabase(peList);
						}
						NextBtnClickAction();
					}
					else
					{
						MessageBox.Show("Hubo un problema al cargar los datos de este batch, revisar los datos en Odoo.", "Batch", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
				}
				else if (textBoxInput.Length > 0 && !acceptPe && waitingConfirmation())
				{
					for (int i = 0; i < articlesGrid.Rows.Count; i++)
					{
						if (foundBox)
						{
							break;
						}
						if (articlesGrid.Rows[i].Cells["SEQ"].Value.ToString().Equals(textBoxInput) && (articlesGrid.Rows[i].Cells["Product_Code"].Value.ToString().Equals(lastValidProduct) || articlesGrid.Rows[i].Cells["Ean_Code"].Value.ToString().Equals(lastValidProduct)) && Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()) && Convert.ToInt32(cellSequenceValue) == Convert.ToInt32(textBoxInput) && !Convert.ToBoolean(articlesGrid.Rows[i].Cells["Finalizado"].Value.ToString()))
						{
							foundBox = true;
							articlesGrid.Rows[i].Cells["Leido"].Value = Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()) + 1;
							string productPe = articlesGrid.Rows[i].Cells["PE"].Value.ToString();
							articlesLeido += 1.0;
							shiftArticles += 1.0;
							lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
							lblPe.Text = "CONFIRMADO";
							panelScanPe.BackColor = Color.LightGreen;
							sound_ok.Play();
							scanInput.Text = null;
							scanInput.Select();
							UpdateProgressBar();
							logArticleLines();
							paintTable(i);
							GetBatchProductivityRecords();
							AddScanToPackingList(productPe, Convert.ToInt32(articlesGrid.Rows[i].Cells["Caja"].Value.ToString()), articlesGrid.Rows[i].Cells["Style"].Value.ToString(), articlesGrid.Rows[i].Cells["COLOR"].Value.ToString(), articlesGrid.Rows[i].Cells["SIZE"].Value.ToString(), articlesGrid.Rows[i].Cells["EAN_Code"].Value.ToString(), 1);
							logPackingList();
							UpdateDoneQtyByOrderNumber(productPe, Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()), articlesGrid.Rows[i].Cells["Product_Code"].Value.ToString(), articlesGrid.Rows[i].Cells["EAN_code"].Value.ToString(), Convert.ToInt32(articlesGrid.Rows[i].Cells["sml_id"].Value.ToString()));
							CheckIfPeIsFinishedAndDoStuff(productPe);
						}
					}
					if (!foundBox)
					{
						sound_error.Play();
						lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
						lblPe.Text = "ERROR: SEQ incorrecta. ESCANEAR ARTÍCULO DE NUEVO";
						panelScanPe.BackColor = Color.Red;
						scanInput.Text = null;
						scanInput.Select();
					}
				}
				else if (isValidCode(textBoxInput) && textBoxInput.Length > 0 && !textBoxInput.Contains(";"))
				{
					if (acceptPe)
					{
						if (!peHasBeenScanned(textBoxInput) && !waitingConfirmation())
						{
							buildTable(textBoxInput);
							peList.Add(textBoxInput);
							sound_ok.Play();
							scanInput.Text = null;
							scanInput.Select();
						}
					}
					else if (!acceptPe && !waitingConfirmation() && peList.Count() == 1)
					{
						StartTimer();
						StartShiftTimer();
						PausePauseTimer();
						for (int i2 = 0; i2 < articlesGrid.Rows.Count; i2++)
						{
							if (foundBox)
							{
								break;
							}
							if ((articlesGrid.Rows[i2].Cells["Product_Code"].Value.ToString().Equals(textBoxInput) || articlesGrid.Rows[i2].Cells["Ean_Code"].Value.Equals(textBoxInput)) && Convert.ToInt32(articlesGrid.Rows[i2].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[i2].Cells["Leido"].Value.ToString()) && !Convert.ToBoolean(articlesGrid.Rows[i2].Cells["Finalizado"].Value.ToString()))
							{
								foundBox = true;
								articlesGrid.Rows[i2].Cells["Leido"].Value = Convert.ToInt32(articlesGrid.Rows[i2].Cells["Leido"].Value.ToString()) + 1;
								string productPe2 = articlesGrid.Rows[i2].Cells["PE"].Value.ToString();
								articlesLeido += 1.0;
								shiftArticles += 1.0;
								lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
								lblPe.Text = "CONFIRMADO. ESCANEAR OTRO ARTÍCULO";
								panelScanPe.BackColor = Color.LightGreen;
								sound_ok.Play();
								scanInput.Text = null;
								scanInput.Select();
								UpdateProgressBar();
								logArticleLines();
								paintTable(i2);
								GetBatchProductivityRecords();
								AddScanToPackingList(productPe2, Convert.ToInt32(articlesGrid.Rows[i2].Cells["Caja"].Value.ToString()), articlesGrid.Rows[i2].Cells["Style"].Value.ToString(), articlesGrid.Rows[i2].Cells["COLOR"].Value.ToString(), articlesGrid.Rows[i2].Cells["SIZE"].Value.ToString(), articlesGrid.Rows[i2].Cells["EAN_Code"].Value.ToString(), 1);
								logPackingList();
								UpdateDoneQtyByOrderNumber(productPe2, Convert.ToInt32(articlesGrid.Rows[i2].Cells["Leido"].Value.ToString()), articlesGrid.Rows[i2].Cells["Product_Code"].Value.ToString(), articlesGrid.Rows[i2].Cells["EAN_code"].Value.ToString(), Convert.ToInt32(articlesGrid.Rows[i2].Cells["sml_id"].Value.ToString()));
								CheckIfPeIsFinishedAndDoStuff(productPe2);
							}
						}
						if (!foundBox)
						{
							lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
							lblPe.Text = "⬆ ⬆ ⬆";
							panelScanPe.BackColor = Color.Beige;
							Speak("SIGUIENTE");
							scanInput.Text = null;
							scanInput.Select();
						}
					}
					else if (!acceptPe && !waitingConfirmation())
					{
						StartTimer();
						StartShiftTimer();
						PausePauseTimer();
						for (int i3 = 0; i3 < articlesGrid.Rows.Count; i3++)
						{
							if (foundInTable)
							{
								break;
							}
							if ((articlesGrid.Rows[i3].Cells["Product_Code"].Value.ToString().Equals(textBoxInput) || articlesGrid.Rows[i3].Cells["Ean_Code"].Value.Equals(textBoxInput)) && Convert.ToInt32(articlesGrid.Rows[i3].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[i3].Cells["Leido"].Value.ToString()) && !Convert.ToBoolean(articlesGrid.Rows[i3].Cells["Finalizado"].Value.ToString()))
							{
								foundInTable = true;
								lastValidProduct = textBoxInput;
								cellSequenceValue = articlesGrid.Rows[i3].Cells["SEQ"].Value.ToString();
								string synthText = "PEDIDO " + Convert.ToInt32(cellSequenceValue) + ". CONFIRMAR";
								lblPe.Text = cellSequenceValue;
								lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 150f);
								panelScanPe.BackColor = Color.LightBlue;
								scanInput.Text = null;
								scanInput.Select();
								Speak(synthText);
							}
						}
						if (!foundInTable)
						{
							lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
							lblPe.Text = "⬆ ⬆ ⬆";
							panelScanPe.BackColor = Color.Beige;
							Speak("SIGUIENTE");
							scanInput.Text = null;
							scanInput.Select();
						}
					}
					else if (!acceptPe && waitingConfirmation() && textBoxInput.Equals(lastValidProduct))
					{
						sound_alert.Play();
						lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
						panelScanPe.BackColor = Color.Yellow;
						scanInput.Text = null;
						scanInput.Select();
					}
					else
					{
						sound_alert.Play();
						lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
						lblPe.Text = "ERROR: CAJA " + Convert.ToInt32(cellSequenceValue) + " NO CONFIRMADA";
						panelScanPe.BackColor = Color.Red;
						scanInput.Text = null;
						scanInput.Select();
						Speak(lblPe.Text.ToString());
					}
				}
				else if (textBoxInput.Length <= seqLength)
				{
					sound_error.Play();
					lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
					lblPe.Text = "ERROR: Escaneo incorrecto";
					panelScanPe.BackColor = Color.Red;
					scanInput.Text = null;
					scanInput.Select();
				}
				else
				{
					lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
					lblPe.Text = "NO ENCONTRADO";
					panelScanPe.BackColor = Color.DeepPink;
					Speak(lblPe.Text.ToString());
					scanInput.Text = null;
					scanInput.Select();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("processScannedInput_ " + ex.Message, "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
			}
		}

		private void processScannedInputECI(string textBoxInput)
		{
			try
			{
				bool foundBox = false;
				if ((textBoxInput.Contains("/OUT/") || textBoxInput.Contains("/INT")) && textBoxInput.Contains(";") && acceptPe)
				{
					string[] source = textBoxInput.Split(';');
					List<string> noDupes = source.Distinct().ToList();
					IEnumerable<string> duplicates = (from result in source
						group result by result).SelectMany((IGrouping<string, string> grp) => grp.Skip(1).Take(1));
					if (duplicates.Count() > 0)
					{
						string message = string.Empty;
						foreach (string item in duplicates)
						{
							message = message + item + "\n";
						}
						MessageBox.Show(message, "Pedidos duplicados", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
					foreach (string peCode in noDupes)
					{
						if ((peCode.Contains("/OUT/") || peCode.Contains("/INT")) && isValidCode(peCode))
						{
							peList.Add(peCode.ToString());
						}
					}
					foreach (string item2 in peList)
					{
						buildTable(item2.ToString());
					}
					sound_ok.Play();
					if (crmLogs)
					{
						InsertRecordsIntoCrmDatabase(peList);
					}
					NextBtnClickAction();
				}
				else if (acceptPe && (textBoxInput.StartsWith("B-") || textBoxInput.StartsWith("BATCH/") || textBoxInput.StartsWith("ECI_") || textBoxInput.StartsWith("VP_") || textBoxInput.StartsWith("WEB_")))
				{
					List<string> noDupes2 = GetOrdersByBatchName(textBoxInput.ToString());
					if (noDupes2.Count > 0)
					{
						foreach (string item3 in noDupes2)
						{
							buildTable(item3.ToString());
						}
						sound_ok.Play();
						if (crmLogs)
						{
							InsertRecordsIntoCrmDatabase(peList);
						}
						NextBtnClickAction();
					}
					else
					{
						MessageBox.Show("Hubo un problema al cargar los datos de este batch", "Batch", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
				}
				else if (isValidCode(textBoxInput) && textBoxInput.Length > 0 && !textBoxInput.Contains(";"))
				{
					if (acceptPe)
					{
						if (!peHasBeenScanned(textBoxInput) && !waitingConfirmation())
						{
							buildTable(textBoxInput);
							peList.Add(textBoxInput);
							sound_ok.Play();
							scanInput.Text = null;
							scanInput.Select();
						}
					}
					else if (!acceptPe && !waitingConfirmation())
					{
						StartTimer();
						StartShiftTimer();
						PausePauseTimer();
						for (int i = 0; i < articlesGrid.Rows.Count; i++)
						{
							if (foundBox)
							{
								break;
							}
							if ((articlesGrid.Rows[i].Cells["Product_Code"].Value.ToString().Equals(textBoxInput) || articlesGrid.Rows[i].Cells["Ean_Code"].Value.Equals(textBoxInput)) && Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()) && !Convert.ToBoolean(articlesGrid.Rows[i].Cells["Finalizado"].Value.ToString()))
							{
								foundBox = true;
								articlesGrid.Rows[i].Cells["Leido"].Value = Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()) + 1;
								string productPe = articlesGrid.Rows[i].Cells["PE"].Value.ToString();
								articlesLeido += 1.0;
								shiftArticles += 1.0;
								lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
								lblPe.Text = "CONFIRMADO. ESCANEAR OTRO ARTÍCULO";
								panelScanPe.BackColor = Color.LightGreen;
								sound_ok.Play();
								scanInput.Text = null;
								scanInput.Select();
								UpdateProgressBar();
								logArticleLines();
								paintTable(i);
								GetBatchProductivityRecords();
								AddScanToPackingList(productPe, Convert.ToInt32(articlesGrid.Rows[i].Cells["Caja"].Value.ToString()), articlesGrid.Rows[i].Cells["Style"].Value.ToString(), articlesGrid.Rows[i].Cells["COLOR"].Value.ToString(), articlesGrid.Rows[i].Cells["SIZE"].Value.ToString(), articlesGrid.Rows[i].Cells["EAN_Code"].Value.ToString(), 1);
								logPackingList();
								UpdateDoneQtyByOrderNumber(productPe, Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()), articlesGrid.Rows[i].Cells["Product_Code"].Value.ToString(), articlesGrid.Rows[i].Cells["EAN_code"].Value.ToString(), Convert.ToInt32(articlesGrid.Rows[i].Cells["sml_id"].Value.ToString()));
								CheckIfPeIsFinishedAndDoStuff(productPe);
							}
						}
						if (!foundBox)
						{
							lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
							lblPe.Text = "⬆ ⬆ ⬆";
							panelScanPe.BackColor = Color.Beige;
							Speak("SIGUIENTE");
							scanInput.Text = null;
							scanInput.Select();
						}
					}
					else
					{
						sound_alert.Play();
						lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
						lblPe.Text = "ERROR";
						panelScanPe.BackColor = Color.Red;
						scanInput.Text = null;
						scanInput.Select();
						Speak(lblPe.Text.ToString());
					}
				}
				else if (textBoxInput.Length <= seqLength)
				{
					sound_error.Play();
					lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
					lblPe.Text = "ERROR: Escaneo incorrecto";
					panelScanPe.BackColor = Color.Red;
					scanInput.Text = null;
					scanInput.Select();
				}
				else
				{
					lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f);
					lblPe.Text = "NO ENCONTRADO";
					panelScanPe.BackColor = Color.DeepPink;
					Speak(lblPe.Text.ToString());
					scanInput.Text = null;
					scanInput.Select();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("processScannedInputECI_" + ex.Message, "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
			}
		}

		private void AddScanToPackingList(string pe, int box, string style, string color, string size, string ean, int qty)
		{
			bool found = false;
			for (int i = 0; i < packingListDt.Rows.Count; i++)
			{
				if (found)
				{
					break;
				}
				if (Convert.ToInt32(packingListDt.Rows[i]["BOX"].ToString()) == box && packingListDt.Rows[i]["STYLE"].Equals(style) && packingListDt.Rows[i]["COLOR"].Equals(color) && packingListDt.Rows[i]["SIZE"].Equals(size) && packingListDt.Rows[i]["EAN"].Equals(ean) && packingListDt.Rows[i]["PE"].Equals(pe))
				{
					if (qty > 1)
					{
						packingListDt.Rows[i]["QTY"] = Convert.ToInt32(packingListDt.Rows[i]["QTY"].ToString()) + qty;
					}
					else
					{
						packingListDt.Rows[i]["QTY"] = Convert.ToInt32(packingListDt.Rows[i]["QTY"].ToString()) + 1;
					}
					found = true;
				}
			}
			if (!found)
			{
				packingListDt.Rows.Add(box, style, color, size, ean, qty, pe);
			}
			packingListDt.DefaultView.Sort = "[PE] ASC, [BOX] ASC, [STYLE] ASC, [SIZE] ASC";
			packingListDt = packingListDt.DefaultView.ToTable();
		}

		private void paintTable(int i)
		{
			if (Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString()) == Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()))
			{
				articlesGrid.Rows[i].DefaultCellStyle.BackColor = Color.LightGreen;
				articlesGrid.Rows[articlesGrid.Rows[i].Index].Selected = true;
				articlesGrid.FirstDisplayedScrollingRowIndex = articlesGrid.Rows[i].Index;
			}
			else if (Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()) && Convert.ToBoolean(articlesGrid.Rows[i].Cells["Finalizado"].Value))
			{
				articlesGrid.Rows[i].DefaultCellStyle.BackColor = Color.Yellow;
				articlesGrid.Rows[articlesGrid.Rows[i].Index].Selected = true;
				articlesGrid.FirstDisplayedScrollingRowIndex = articlesGrid.Rows[i].Index;
			}
			else if (Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()))
			{
				articlesGrid.Rows[articlesGrid.Rows[i].Index].Selected = true;
				articlesGrid.FirstDisplayedScrollingRowIndex = articlesGrid.Rows[i].Index;
			}
		}

		private void logArticleLines()
		{
			try
			{
				string logFileName = "last_prep_" + company + ".txt";
				TextWriter writer = new StreamWriter(Path.Combine(logFolderPath, logFileName));
				for (int i = 0; i < articlesGrid.Rows.Count; i++)
				{
					for (int j = 0; j < articlesGrid.Columns.Count; j++)
					{
						writer.Write(articlesGrid.Rows[i].Cells[j].Value.ToString() + ";");
					}
					writer.WriteLine("");
				}
				writer.Close();
			}
			catch (Exception ex)
			{
				MessageBox.Show("logArticleLines_ " + ex.Message, "Error");
			}
		}

		private void logPackingList()
		{
			try
			{
				string logFileName = "packing_list_" + company + ".txt";
				TextWriter writer = new StreamWriter(Path.Combine(logFolderPath, logFileName));
				for (int i = 0; i < packingListDt.Rows.Count; i++)
				{
					for (int j = 0; j < packingListDt.Columns.Count; j++)
					{
						writer.Write(packingListDt.Rows[i][j].ToString() + ";");
					}
					writer.WriteLine("");
				}
				writer.Close();
			}
			catch (Exception ex)
			{
				MessageBox.Show("logPackingList_ " + ex.Message, "Error");
			}
		}

		// Modo prueba: anota lo que el programa habria escrito, en lugar de escribirlo.
		private void LogPrueba(string texto)
		{
			try
			{
				File.AppendAllText(Path.Combine(logFolderPath, "prueba_" + (company ?? "") + ".txt"), DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + texto + Environment.NewLine);
			}
			catch (Exception ex)
			{
				ex.ToString();
			}
		}

		// Modo prueba: suma de lo leido en el programa para un pedido (sustituye a GetDoneQtySum).
		private int SumaLeidoEnMemoria(string order)
		{
			int suma = 0;
			for (int i = 0; i < articlesGrid.Rows.Count; i++)
			{
				if (articlesGrid.Rows[i].Cells["PE"].Value.ToString().Equals(order))
				{
					suma += Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString());
				}
			}
			return suma;
		}

		// Etiqueta de caja con datos de ejemplo, para ver como sale impresa.
		// No toca Odoo, ni la base de datos, ni la oleada cargada.
		private void imprimirEtiquetaPrueba_Click(object sender, EventArgs e)
		{
			if (!printLabels)
			{
				MessageBox.Show("Activar antes Opciones > Imprimir etiquetas caja.", "Etiqueta de prueba", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				return;
			}
			string empresaActual = company;
			if (string.IsNullOrEmpty(company))
			{
				company = "EFFE";
			}
			GenerateLabel("001", "EFFEC/OUT/00000", "1/1", "K00 - TIENDA DE PRUEBA", "España", last: false, "S00000", "CJ665000000");
			company = empresaActual;
			scanInput.Select();
		}

		// ---------------- Modo matricula KOROSHI (EFFE) ----------------

		private void AbrirMatriculas()
		{
			using (MatriculasForm form = new MatriculasForm(matriculasPorSeq, seqLength, ValidarSeqMatricula, ValidarMatricula, GuardarMatriculas, null))
			{
				form.ShowDialog(this);
			}
			scanInput.Text = null;
			scanInput.Select();
		}

		// Lee una matricula para cerrar una caja del SEQ cuando no hay ninguna preregistrada. Devuelve null si se cancela.
		private string PedirMatricula(string seq)
		{
			sound_alert.Play();
			using (MatriculasForm form = new MatriculasForm(matriculasPorSeq, seqLength, ValidarSeqMatricula, ValidarMatricula, GuardarMatriculas, seq))
			{
				return (form.ShowDialog(this) == DialogResult.OK) ? form.MatriculaLeida : null;
			}
		}

		private string ValidarSeqMatricula(string seq)
		{
			foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
			{
				if (row.Cells["SEQ"].Value.ToString().Equals(seq) && !Convert.ToBoolean(row.Cells["Finalizado"].Value.ToString()))
				{
					return null;
				}
			}
			return "SEQ " + seq + " no existe en la oleada o el pedido ya está terminado";
		}

		// Solo lectura: formato, que exista en zebra.label y que no este en un paquete con contenido.
		private string ValidarMatricula(string matricula)
		{
			if (!Regex.IsMatch(matricula, "^" + PrefijoMatricula + "[A-Z0-9]+$"))
			{
				return "formato no válido (" + PrefijoMatricula + "...)";
			}
			if (matriculasUsadas.Contains(matricula))
			{
				return "ya se ha usado en esta sesión";
			}
			try
			{
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand existe = new NpgsqlCommand("select count(*) from zebra_label where name = @matricula;", cSql.dbConn);
					existe.Parameters.AddWithValue("@matricula", matricula);
					if (Convert.ToInt64(existe.ExecuteScalar()) == 0)
					{
						return "no existe en Odoo (Etiquetas Zebra)";
					}
					NpgsqlCommand usada = new NpgsqlCommand("select count(*) from stock_quant_package pk where pk.name = @matricula and (exists (select 1 from stock_quant q where q.package_id = pk.id and q.quantity > 0) or exists (select 1 from stock_move_line ml where ml.result_package_id = pk.id and ml.state not in ('done', 'cancel')));", cSql.dbConn);
					usada.Parameters.AddWithValue("@matricula", matricula);
					if (Convert.ToInt64(usada.ExecuteScalar()) > 0)
					{
						return "ya es un paquete con contenido en Odoo";
					}
					cSql.dbConn.Close();
				}
			}
			catch (Exception ex)
			{
				return "error al validar en Odoo: " + ex.Message;
			}
			return null;
		}

		private void GuardarMatriculas()
		{
			try
			{
				List<string> lineas = new List<string>();
				foreach (string seq in matriculasPorSeq.Keys.OrderBy((string s) => s))
				{
					string pe = "";
					foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
					{
						if (row.Cells["SEQ"].Value.ToString().Equals(seq))
						{
							pe = row.Cells["PE"].Value.ToString();
							break;
						}
					}
					lineas.Add(seq + ";" + pe + ";" + string.Join(",", matriculasPorSeq[seq]));
				}
				File.WriteAllLines(Path.Combine(logFolderPath, "matriculas_" + company + ".txt"), lineas);
			}
			catch (Exception ex)
			{
				MessageBox.Show("GuardarMatriculas_ " + ex.Message, "Error");
			}
		}

		private HashSet<int> IndicesPedido(string pe)
		{
			HashSet<int> indexes = new HashSet<int>();
			for (int i = 0; i < articlesGrid.Rows.Count; i++)
			{
				if (articlesGrid.Rows[i].Cells["PE"].Value.ToString().Equals(pe) && !Convert.ToBoolean(articlesGrid.Rows[i].Cells["Finalizado"].Value.ToString()))
				{
					indexes.Add(i);
				}
			}
			return indexes;
		}

		// Cierra en Odoo la caja abierta del pedido: la accion de servidor pone las lineas
		// leidas sin paquete en un paquete con el nombre de la matricula. Si va bien, vuelve
		// a leer las lineas del pedido (Odoo las parte al empaquetar). Si falla, la caja
		// queda abierta. Si la caja esta vacia no hace nada y devuelve true.
		private bool CerrarCajaEnOdoo(string seq, string pe, string box, out string matricula)
		{
			matricula = string.Empty;
			int udsCaja = (from row in packingListDt.AsEnumerable()
				where row["PE"].ToString().Equals(pe)
				where row["BOX"].ToString().Equals(box)
				select row.Field<int>("QTY")).Sum();
			if (udsCaja <= 0)
			{
				return true;
			}
			List<string> cola = null;
			bool deLaCola = false;
			XmlRpcStruct extra;
			if (matriculaAuto)
			{
				// La matricula la genera Odoo (siguiente CJ de la secuencia) y la devuelve
				extra = new XmlRpcStruct { { "generar_matricula", true } };
			}
			else
			{
				deLaCola = matriculasPorSeq.TryGetValue(seq, out cola) && cola.Count > 0;
				matricula = deLaCola ? cola[0] : PedirMatricula(seq);
				if (string.IsNullOrEmpty(matricula))
				{
					matricula = string.Empty;
					sound_error.Play();
					lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
					lblPe.Text = "CAJA NO CERRADA:\nFALTA LA MATRÍCULA";
					panelScanPe.BackColor = Color.Red;
					return false;
				}
				extra = new XmlRpcStruct { { "matricula", matricula } };
			}
			lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
			lblPe.Text = "ESPERE,\nCERRANDO CAJA " + box + (matriculaAuto ? "" : (" (" + matricula + ")")) + "...";
			panelScanPe.BackColor = default(Color);
			lblPe.Refresh();
			OdooAccion.Resultado resultado;
			if (modoPrueba)
			{
				if (matriculaAuto)
				{
					matricula = "CJPRUEBA" + DateTime.Now.ToString("HHmmss");
				}
				LogPrueba("Empaquetar caja no hecho: " + pe + " SEQ " + seq + " caja " + box + " (" + udsCaja + " uds) matricula " + matricula);
				resultado = new OdooAccion.Resultado
				{
					Ok = true
				};
			}
			else
			{
				Cursor = Cursors.WaitCursor;
				resultado = odooAccion.EjecutarAccionPorNombre(accionEmpaquetarId, pe, db, extra);
				Cursor = Cursors.Default;
				if (resultado.Ok && matriculaAuto)
				{
					matricula = resultado.Matricula;
					if (string.IsNullOrEmpty(matricula))
					{
						MessageBox.Show("La caja " + box + " del pedido " + pe + " se ha cerrado en Odoo, pero Odoo no ha devuelto la matrícula y no saldrá en la etiqueta. Revisar la acción de Odoo (odoo_accion_empaquetar_id).", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
				}
			}
			if (!resultado.Ok)
			{
				sound_error.Play();
				lblPe.Text = "ERROR: CAJA " + box + " NO CERRADA";
				panelScanPe.BackColor = Color.Red;
				string mensaje = "No se ha podido cerrar la caja " + box + " del pedido " + pe + " (SEQ " + seq + ")" + (matriculaAuto ? "" : (" con la matrícula " + matricula)) + ".\n\n" + resultado.Mensaje + "\n\nLa caja sigue abierta. Para volver a intentarlo: CAMBIAR CAJA y el SEQ.";
				if (deLaCola)
				{
					if (MessageBox.Show(mensaje + "\n\n¿Descartar la matrícula " + matricula + " y usar otra?", "Odoo: caja no cerrada", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes)
					{
						cola.RemoveAt(0);
						GuardarMatriculas();
					}
				}
				else
				{
					MessageBox.Show(mensaje, "Odoo: caja no cerrada", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				}
				matricula = string.Empty;
				return false;
			}
			if (deLaCola)
			{
				cola.RemoveAt(0);
			}
			matriculasUsadas.Add(matricula);
			if (!matriculaAuto)
			{
				GuardarMatriculas();
			}
			try
			{
				File.AppendAllText(Path.Combine(logFolderPath, "cajas_" + company + ".txt"), DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + ";" + nombreOleada + ";" + pe + ";" + seq + ";" + box + ";" + udsCaja + ";" + matricula + Environment.NewLine);
			}
			catch (Exception ex)
			{
				ex.ToString();
			}
			if (!modoPrueba)
			{
				RecargarLineasPedido(pe);
			}
			return true;
		}

		// Vuelve a leer de Odoo las lineas de un pedido y las pone en el mismo sitio de la
		// tabla, conservando SEQ y caja. Necesario despues de empaquetar: Odoo parte las
		// lineas y los sml_id que tenia el programa ya no sirven.
		private void RecargarLineasPedido(string pe)
		{
			try
			{
				DataTable nuevas = new DataTable();
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand obj = new NpgsqlCommand(queryInicial, cSql.dbConn)
					{
						CommandTimeout = 120
					};
					obj.Parameters.AddWithValue("@company_id", db);
					obj.Parameters.AddWithValue("@order", pe);
					using (NpgsqlDataAdapter adapter = new NpgsqlDataAdapter(obj))
					{
						adapter.Fill(nuevas);
					}
				}
				if (nuevas.Rows.Count == 0)
				{
					MessageBox.Show("No se han podido volver a leer las líneas del pedido " + pe + ". Volver a cargar la oleada antes de seguir.", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					return;
				}
				int primero = -1;
				string seq = "";
				object caja = 1;
				for (int i = dataTableSource.Rows.Count - 1; i >= 0; i--)
				{
					if (dataTableSource.Rows[i]["PE"].ToString().Equals(pe))
					{
						primero = i;
						seq = dataTableSource.Rows[i]["SEQ"].ToString();
						caja = dataTableSource.Rows[i]["Caja"];
						dataTableSource.Rows.RemoveAt(i);
					}
				}
				if (primero < 0)
				{
					primero = dataTableSource.Rows.Count;
				}
				for (int j = 0; j < nuevas.Rows.Count; j++)
				{
					DataRow fila = dataTableSource.NewRow();
					foreach (DataColumn columna in nuevas.Columns)
					{
						if (dataTableSource.Columns.Contains(columna.ColumnName))
						{
							fila[columna.ColumnName] = nuevas.Rows[j][columna];
						}
					}
					fila["SEQ"] = seq;
					fila["Caja"] = caja;
					fila["Finalizado"] = false;
					dataTableSource.Rows.InsertAt(fila, primero + j);
				}
				foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
				{
					if (row.Cells["PE"].Value.ToString().Equals(pe))
					{
						row.DefaultCellStyle.BackColor = (Convert.ToInt32(row.Cells["QTY"].Value.ToString()) == Convert.ToInt32(row.Cells["Leido"].Value.ToString())) ? Color.LightGreen : Color.Empty;
					}
				}
				logArticleLines();
			}
			catch (Exception ex)
			{
				MessageBox.Show("RecargarLineasPedido_ " + ex.Message + "\nVolver a cargar la oleada antes de seguir.", "Error " + pe, MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private async void CheckIfPeIsFinishedAndDoStuff(string pe)
		{
			try
			{
				int totalQtyPe = 0;
				int currentReadQtyPe = 0;
				string seq = "";
				string box = "";
				int lines = 0;
				HashSet<int> indexes = new HashSet<int>();
				lastPE = pe;
				if (pe.Length <= 0)
				{
					return;
				}
				for (int i = 0; i < articlesGrid.Rows.Count; i++)
				{
					if (articlesGrid.Rows[i].Cells["PE"].Value.ToString().Equals(pe))
					{
						indexes.Add(i);
						totalQtyPe += Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString());
						currentReadQtyPe += Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString());
						seq = articlesGrid.Rows[i].Cells["SEQ"].Value.ToString();
						box = articlesGrid.Rows[i].Cells["Caja"].Value.ToString();
						lines++;
					}
				}
				if (!ECImode && totalQtyPe == currentReadQtyPe && !VPmode)
				{
					if (currentReadQtyPe == GetDoneQtySum(pe))
					{
						DataTable temporalClient = new DataTable();
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						temporalClient = FetchClientInfoFromLivraison(company, pe);
						string cliente = temporalClient.Rows[0]["Name"].ToString();
						temporalClient.Rows[0]["Address"].ToString();
						temporalClient.Rows[0]["Complement"].ToString();
						temporalClient.Rows[0]["CodePostal"].ToString();
						temporalClient.Rows[0]["Ville"].ToString();
						temporalClient.Rows[0]["CodeRegion"].ToString();
						string pays = temporalClient.Rows[0]["Pays"].ToString();
						temporalClient.Rows[0]["Telephone"].ToString();
						temporalClient.Rows[0]["Email"].ToString();
						_ = string.Empty;
						if (DateTime.TryParse(temporalClient.Rows[0]["DeliveryDate"].ToString(), out var deliveryDateTime))
						{
							deliveryDateTime = Convert.ToDateTime(temporalClient.Rows[0]["DeliveryDate"].ToString());
							_ = $"{deliveryDateTime:dd/MM/yyyy}";
						}
						if (cliente == string.Empty && pe.Contains("/INT"))
						{
							cliente = FetchLocationName(company, pe);
						}
						if (cliente != string.Empty)
						{
							sound_final.Play();
							if (generateShipmentLabels && (db == companyIds["NATH"] || db == companyIds["ALAN"]))
							{
								lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
								panelScanPe.BackColor = default(Color);
								lblPe.Text = "ESPERE,\nVALIDANDO PEDIDO EN ODOO...";
								if (await Task.Run(() => GenerateCarrierLabelInOdoo(pe, temporalClient)))
								{
									lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
									lblPe.Text = "...VALIDADO \ud83d\udc4d";
									panelScanPe.BackColor = Color.LightGreen;
								}
								else
								{
									lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
									lblPe.Text = "...HUBO UN ERROR \ud83d\udc80";
									panelScanPe.BackColor = Color.Red;
								}
							}
							string matricula = string.Empty;
							if (MatriculaActiva)
							{
								// Modo matricula: cerrar la ultima caja en Odoo; si falla, el pedido no se termina
								if (!CerrarCajaEnOdoo(seq, pe, box, out matricula))
								{
									return;
								}
								indexes = IndicesPedido(pe);
							}
							string origin = string.Empty;
							if (company.Equals("EFFE"))
							{
								origin = temporalClient.Rows[0]["Origin"].ToString();
							}
							GenerateLabel(seq, pe, box, cliente, pays, last: true, origin, matricula);
							if (sendEmails)
							{
								sendEmailOnPeFinishedToConfigUser(pe, seq, currentReadQtyPe, cliente);
								sendEmailOnPeFinishedToGestor(pe, seq, currentReadQtyPe, cliente);
							}
							await Task.Run(delegate
							{
								if (crmLogs)
								{
									InsertOrderDoubleCheckingLogCrm(pe);
								}
							});
							FinishOrder(indexes, seq);
						}
						else
						{
							MessageBox.Show("Problema con el cliente", "Atencion", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
						}
					}
					else
					{
						MessageBox.Show("❌❌❌ Qty_done en Odoo es diferente de la que hay en el programa!!! ❌❌❌", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
				}
				else if (ECImode)
				{
					if (totalQtyPe == currentReadQtyPe)
					{
						if (lines > 1 || totalQtyPe > 1)
						{
							sound_eci.Play();
						}
						else
						{
							sound_final.Play();
						}
						new DataTable();
						_ = string.Empty;
						_ = string.Empty;
						DataTable dataTable = FetchClientInfoFromLivraison(company, pe);
						string cliente2 = dataTable.Rows[0]["Name"].ToString();
						string pays2 = dataTable.Rows[0]["Pays"].ToString();
						if (cliente2 == string.Empty && pe.Contains("/INT"))
						{
							cliente2 = FetchLocationName(company, pe);
						}
						if (cliente2 != string.Empty)
						{
							GenerateLabel(seq, pe, box, cliente2, pays2, last: true, string.Empty);
							if (sendEmails)
							{
								sendEmailOnPeFinishedToConfigUser(pe, seq, currentReadQtyPe, cliente2);
								sendEmailOnPeFinishedToGestor(pe, seq, currentReadQtyPe, cliente2);
							}
							await Task.Run(delegate
							{
								if (crmLogs)
								{
									InsertOrderDoubleCheckingLogCrm(pe);
								}
							});
							FinishOrder(indexes, seq);
						}
						else
						{
							MessageBox.Show("Problema con el cliente", "Atencion", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
						}
					}
					else
					{
						changeBox(seq, increment: true);
					}
				}
				else if (VPmode && totalQtyPe == currentReadQtyPe)
				{
					sound_final.Play();
					new DataTable();
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					DataTable temporalClient2 = FetchClientInfoFromLivraison(company, pe);
					string cliente3 = temporalClient2.Rows[0]["Name"].ToString();
					temporalClient2.Rows[0]["Address"].ToString();
					temporalClient2.Rows[0]["Complement"].ToString();
					temporalClient2.Rows[0]["CodePostal"].ToString();
					temporalClient2.Rows[0]["Ville"].ToString();
					temporalClient2.Rows[0]["CodeRegion"].ToString();
					string pays3 = temporalClient2.Rows[0]["Pays"].ToString();
					temporalClient2.Rows[0]["Telephone"].ToString();
					temporalClient2.Rows[0]["Email"].ToString();
					_ = string.Empty;
					if (DateTime.TryParse(temporalClient2.Rows[0]["DeliveryDate"].ToString(), out var deliveryDateTime2))
					{
						deliveryDateTime2 = Convert.ToDateTime(temporalClient2.Rows[0]["DeliveryDate"].ToString());
						_ = $"{deliveryDateTime2:dd/MM/yyyy}";
					}
					if (cliente3.Length > 0)
					{
						GenerateLabel(seq, pe, box, cliente3, pays3, last: true, string.Empty);
					}
					if (sendEmails)
					{
						sendEmailOnPeFinishedToConfigUser(pe, seq, currentReadQtyPe, cliente3);
						sendEmailOnPeFinishedToGestor(pe, seq, currentReadQtyPe, cliente3);
					}
					if (crmLogs)
					{
						await Task.Run(delegate
						{
							InsertOrderDoubleCheckingLogCrm(pe);
						});
					}
					FinishOrder(indexes, pe);
				}
				if (articlesTotal == articlesLeido)
				{
					PauseTimer();
					PauseShiftTimer();
					PausePauseTimer();
					if (crmLogs)
					{
						InsertProductivity();
					}
					lblPe.Text = "OLEADA TERMINADA";
					if (sendEmails)
					{
						sendEmailOnOleadaFinishedToConfigUser();
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("CheckIfPeIsFinishedAndDoStuff_" + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private async void sendEmailOnPeFinishedToConfigUser(string pedido, string sequential, int cantidadArticulos, string nombreCliente)
		{
			if (modoPrueba)
			{
				LogPrueba("Correo (pedido terminado, usuario) no enviado: " + pedido);
				return;
			}
			if (!sendEmails)
			{
				return;
			}
			string emailAddress = "";
			double progreso = articlesLeido / articlesTotal * 100.0;
			progreso = Math.Round(progreso, 0, MidpointRounding.AwayFromZero);
			try
			{
				emailAddress = ReturnSetting("email");
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
			ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
			SmtpClient mailClient = new SmtpClient("smtp.office365.com", 587);
			try
			{
				MailMessage message = new MailMessage("robot@nath.es", emailAddress, "Finalización pedido " + sequential + " oleada " + nombreOleada + " (" + company + ").", "Buenos días, \n\n Informamos que el pedido nº " + pedido + " (" + sequential + ") se ha finalizado. \n Nº artículos: " + cantidadArticulos + "\n Cliente: " + nombreCliente + ".\n Progreso oleada: " + progreso + "%\n\nSaludos cordiales.");
				try
				{
					mailClient.Credentials = new NetworkCredential("robot@nath.es", "Root1234");
					mailClient.EnableSsl = true;
					try
					{
						await Task.Run(delegate
						{
							mailClient.Send(message);
						});
					}
					catch (Exception ex2)
					{
						MessageBox.Show("sendEmailOnPeFinishedToConfigUser_ " + ex2, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					}
				}
				finally
				{
					if (message != null)
					{
						((IDisposable)message).Dispose();
					}
				}
			}
			finally
			{
				if (mailClient != null)
				{
					((IDisposable)mailClient).Dispose();
				}
			}
		}

		private async void sendEmailOnPeFinishedToGestor(string pedido, string sequential, int cantidadArticulos, string nombreCliente)
		{
			if (modoPrueba)
			{
				LogPrueba("Correo (pedido terminado, gestor) no enviado: " + pedido);
				return;
			}
			try
			{
				string emailAddress = ReturnSetting("email_pack").ToString();
				string dbName = "";
				switch (company)
				{
				case "NATH":
					dbName = "NATH";
					break;
				case "CODE":
					dbName = "CODE 22";
					break;
				case "ALAN":
					dbName = "ORY";
					break;
				case "TCN":
					dbName = "TCN";
					break;
				case "TTUC":
					dbName = "TUC TUC";
					break;
				case "EFFE":
					dbName = "EFFECTIVE";
					break;
				}
				DateTime today = DateTime.Today;
				ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
				SmtpClient mailClient = new SmtpClient("smtp.office365.com", 587);
				try
				{
					MailMessage message = new MailMessage("robot@nath.es", emailAddress, "PList - " + sequential + " - " + pedido + " - " + nombreCliente + " - " + today.ToString("dd/MM/yyyy") + " (" + dbName + ").", "Buenos días, \n\n Informamos que el pedido " + pedido + " (" + sequential + ") se ha finalizado.\n Oleada: " + nombreOleada + "\n Nº artículos: " + cantidadArticulos + "\n Cliente: " + nombreCliente + "\n Adjuntamos Packing List.\n\nSaludos cordiales.");
					try
					{
						mailClient.Credentials = new NetworkCredential("robot@nath.es", "Root1234");
						mailClient.EnableSsl = true;
						pedido = pedido.Replace("/", "");
						string packingFilename = Path.Combine(pdfPackingPath, "PKL_" + dbName + "_" + pedido + ".pdf");
						if (Directory.Exists(pdfPackingPath) && File.Exists(packingFilename))
						{
							message.Attachments.Add(new Attachment(packingFilename));
							try
							{
								await Task.Run(delegate
								{
									mailClient.Send(message);
								});
							}
							catch (Exception ex)
							{
								MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
							}
						}
						else
						{
							MessageBox.Show("sendEmailOnPeFinishedToGestor_ No existe el archivo o el directorio del Packing List", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
						}
					}
					finally
					{
						if (message != null)
						{
							((IDisposable)message).Dispose();
						}
					}
				}
				finally
				{
					if (mailClient != null)
					{
						((IDisposable)mailClient).Dispose();
					}
				}
			}
			catch (Exception ex2)
			{
				MessageBox.Show("sendEmailOnPeFinishedToGestor_ " + ex2, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private async void sendEmailOnOleadaFinishedToConfigUser()
		{
			if (modoPrueba)
			{
				LogPrueba("Correo (oleada terminada) no enviado");
				return;
			}
			string emailAddress = "";
			try
			{
				emailAddress = ReturnSetting("email");
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
			string logFilename = Path.Combine(logFolderPath, "last_prep_" + company + ".txt");
			string maxSeq = (from DataGridViewRow row in articlesGrid.Rows
				where row.Cells["SEQ"].FormattedValue.ToString() != string.Empty
				select Convert.ToInt32(row.Cells["SEQ"].FormattedValue)).Max().ToString();
			ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
			SmtpClient mailClient = new SmtpClient("smtp.office365.com", 587);
			try
			{
				MailMessage message = new MailMessage("robot@nath.es", emailAddress, "Finalización oleada " + nombreOleada + " (" + company + ").", "Buenos días, \n\n Informamos que la oleada " + nombreOleada + " (" + company + ") se ha finalizado. \n Nº pedidos: " + maxSeq + "\n Total artículos: " + articlesTotal + "\n Tiempo total: " + _currentElapsedTime.ToString() + "\n Articulos / hora: " + productivity + "\n\nSaludos cordiales.");
				try
				{
					mailClient.Credentials = new NetworkCredential("robot@nath.es", "Root1234");
					mailClient.EnableSsl = true;
					message.Attachments.Add(new Attachment(logFilename));
					try
					{
						await Task.Run(delegate
						{
							mailClient.Send(message);
						});
					}
					catch (Exception ex2)
					{
						MessageBox.Show("sendEmailOnOleadaFinishedToConfigUser_ " + ex2.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					}
				}
				finally
				{
					if (message != null)
					{
						((IDisposable)message).Dispose();
					}
				}
			}
			finally
			{
				if (mailClient != null)
				{
					((IDisposable)mailClient).Dispose();
				}
			}
		}

		private bool waitingConfirmation()
		{
			bool isConfirmationText = false;
			if (lblPe.Text.Length == seqLength)
			{
				isConfirmationText = true;
			}
			return isConfirmationText;
		}

		private bool isValidCode(string scannedInput)
		{
			bool valid = false;
			try
			{
				if ((scannedInput.Contains("/OUT/") || scannedInput.Contains("/INT")) && acceptPe)
				{
					using (ConnectionSQL cSql = new ConnectionSQL(company))
					{
						cSql.dbConn.Open();
						NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryCheckIfOrderStateIsAssigned, cSql.dbConn);
						npgsqlCommand.Parameters.AddWithValue("@order", scannedInput);
						if (company.Equals("TTUC"))
						{
							if (scannedInput.StartsWith("W_CAD"))
							{
								db = companyIds["TTUC_CAD"];
							}
							else if (scannedInput.StartsWith("W_COP"))
							{
								db = companyIds["TTUC_COP"];
							}
							else if (scannedInput.StartsWith("W_USA"))
							{
								db = companyIds["TTUC_USA"];
							}
						}
						if (company.Equals("ALAN") && scannedInput.StartsWith("CAREY"))
						{
							db = companyIds["CAREY"];
						}
						npgsqlCommand.Parameters.AddWithValue("@company_id", db);
						NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
						if (reader.HasRows)
						{
							valid = true;
							reader.Close();
						}
						cSql.dbConn.Close();
					}
				}
				else if (acceptPe && (scannedInput.StartsWith("B-") || scannedInput.StartsWith("BATCH/") || scannedInput.StartsWith("ECI_") || scannedInput.StartsWith("VP_") || scannedInput.StartsWith("WEB_")))
				{
					valid = true;
				}
				else if (!acceptPe)
				{
					foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
					{
						if (scannedInput.Equals(row.Cells["EAN_Code"].Value.ToString()) || scannedInput.Equals(row.Cells["Product_code"].Value.ToString()))
						{
							valid = true;
							break;
						}
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("isValidCode_ " + ex.Message, "Error " + scannedInput, MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return valid;
		}

		private bool peHasBeenScanned(string peCode)
		{
			bool status = false;
			foreach (DataRow row in dataTableSource.Rows)
			{
				if (row["PE"].Equals(peCode))
				{
					status = true;
					break;
				}
			}
			return status;
		}

		private void nextBtn_Click(object sender, EventArgs e)
		{
			if (crmLogs)
			{
				InsertRecordsIntoCrmDatabase(peList);
			}
			NextBtnClickAction();
		}

		private void NextBtnClickAction()
		{
			acceptPe = false;
			lblPe.Text = "ESCANEAR ARTÍCULO";
			panelScanPe.BackColor = default(Color);
			scanInput.Text = null;
			scanInput.Select();
			nextBtn.Enabled = false;
			nextBoxBtn.Enabled = true;
			filtroPendBtn.Enabled = true;
			pendingArticlesBtn.Enabled = true;
			pauseTimerBtn.Enabled = true;
			productivityBtn.Enabled = true;
			pendientesPedidoBox.Enabled = true;
			pklTemporalTxt.Enabled = true;
			boxLblPrintTxt.Enabled = true;
			if (!ECImode)
			{
				pklNoAcabadoTxt.Enabled = true;
			}
			foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
			{
				articlesTotal += Convert.ToDouble(row.Cells["QTY"].Value.ToString());
				articlesLeido += Convert.ToDouble(row.Cells["Leido"].Value.ToString());
				paintTable(row.Index);
			}
			UpdateProgressBar();
			if (MatriculaActiva && !matriculaAuto)
			{
				AbrirMatriculas();
			}
		}

		private void progressBarTotal_Paint(object sender, PaintEventArgs e)
		{
			try
			{
				leidoPercent = Math.Round(articlesLeido * 100.0 / articlesTotal, 2);
				StringFormat format = new StringFormat();
				format.LineAlignment = StringAlignment.Center;
				format.Alignment = StringAlignment.Center;
				e.Graphics.FillRectangle(Brushes.Silver, new System.Drawing.Rectangle(0, 0, progressBarTotal.Width, progressBarTotal.Height));
				if (articlesGrid != null)
				{
					if (articlesLeido <= articlesTotal)
					{
						e.Graphics.FillRectangle(Brushes.LightGreen, new System.Drawing.Rectangle(0, 0, (int)Math.Round(leidoPercent * (double)progressBarTotal.Width / 100.0), progressBarTotal.Height));
					}
					else
					{
						e.Graphics.FillRectangle(Brushes.Yellow, new System.Drawing.Rectangle(0, 0, (int)Math.Round(leidoPercent * (double)progressBarTotal.Width / 100.0), progressBarTotal.Height));
					}
					e.Graphics.DrawString(articlesLeido + " de " + articlesTotal, nextBtn.Font, Brushes.Black, progressBarTotal.ClientRectangle, format);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("progressBarTotal_Paint_ " + ex.Message);
			}
		}

		private void UpdateProgressBar()
		{
			try
			{
				progressBarTotal.Invalidate();
			}
			catch (Exception ex)
			{
				MessageBox.Show("UpdateProgressBar_ " + ex.Message);
			}
		}

		private void recoverLastLines()
		{
			try
			{
				string logFileName = "last_prep_" + company + ".txt";
				string logFilePathName = Path.Combine(logFolderPath, logFileName);
				if (!Directory.Exists(logFolderPath) || !File.Exists(logFilePathName))
				{
					resetFormOnDbChange();
					panelScanPe.Visible = false;
					panelTable.Visible = false;
					progressBarTotal.Visible = false;
					MessageBox.Show("No hay archivo de Logs", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					return;
				}
				string[] lines = File.ReadAllLines(logFilePathName);
				string lastRowValue = string.Empty;
				if (lines.Length != 0)
				{
					DataTable dTable = new DataTable();
					DataColumn PE = new DataColumn("PE");
					PE.DataType = Type.GetType("System.String");
					dTable.Columns.Add(PE);
					DataColumn Style = new DataColumn("Style");
					Style.DataType = Type.GetType("System.String");
					dTable.Columns.Add(Style);
					DataColumn COLOR = new DataColumn("COLOR");
					COLOR.DataType = Type.GetType("System.String");
					dTable.Columns.Add(COLOR);
					DataColumn SIZE = new DataColumn("SIZE");
					SIZE.DataType = Type.GetType("System.String");
					dTable.Columns.Add(SIZE);
					DataColumn Product_code = new DataColumn("Product_code");
					Product_code.DataType = Type.GetType("System.String");
					dTable.Columns.Add(Product_code);
					DataColumn EAN_Code = new DataColumn("EAN_Code");
					EAN_Code.DataType = Type.GetType("System.String");
					dTable.Columns.Add(EAN_Code);
					DataColumn QTY = new DataColumn("QTY");
					QTY.DataType = Type.GetType("System.String");
					dTable.Columns.Add(QTY);
					DataColumn Leido = new DataColumn("Leido");
					Leido.DataType = Type.GetType("System.String");
					dTable.Columns.Add(Leido);
					DataColumn sml_id = new DataColumn("sml_id");
					sml_id.DataType = Type.GetType("System.String");
					dTable.Columns.Add(sml_id);
					DataColumn li_intitule = new DataColumn("LI_Intitule");
					sml_id.DataType = Type.GetType("System.String");
					dTable.Columns.Add(li_intitule);
					DataColumn veepee_product_id = new DataColumn("veepee_product_id");
					sml_id.DataType = Type.GetType("System.String");
					dTable.Columns.Add(veepee_product_id);
					DataColumn li_complement = new DataColumn("LI_Complement");
					sml_id.DataType = Type.GetType("System.String");
					dTable.Columns.Add(li_complement);
					DataColumn li_pallet = new DataColumn("LI_Pallet");
					sml_id.DataType = Type.GetType("System.String");
					dTable.Columns.Add(li_pallet);
					DataColumn veepee_ref = new DataColumn("veepee_ref");
					sml_id.DataType = Type.GetType("System.String");
					dTable.Columns.Add(veepee_ref);
					DataColumn SEQ = new DataColumn("SEQ");
					SEQ.DataType = Type.GetType("System.String");
					dTable.Columns.Add(SEQ);
					DataColumn Caja = new DataColumn("Caja");
					Caja.DataType = Type.GetType("System.String");
					dTable.Columns.Add(Caja);
					DataColumn Finalizado = new DataColumn("Finalizado");
					Finalizado.DataType = typeof(bool);
					dTable.Columns.Add(Finalizado);
					resetFormOnDbChange();
					nextBtn.Enabled = false;
					nextBoxBtn.Enabled = true;
					filtroPendBtn.Enabled = true;
					pendingArticlesBtn.Enabled = true;
					pauseTimerBtn.Enabled = true;
					productivityBtn.Enabled = true;
					pklTemporalTxt.Enabled = true;
					pendientesPedidoBox.Enabled = true;
					if (!ECImode)
					{
						pklNoAcabadoTxt.Enabled = true;
					}
					acceptPe = false;
					for (int i = 0; i < lines.Count(); i++)
					{
						DataRow dRow = dTable.NewRow();
						string[] values = lines[i].Split(';');
						for (int j = 0; j < values.Count() && j < dTable.Columns.Count; j++)
						{
							dRow[j] = values[j];
						}
						dTable.Rows.Add(dRow);
					}
					articlesGrid.DataSource = dTable;
					if (articlesGrid.Columns.Contains("sml_id"))
					{
						articlesGrid.Columns["sml_id"].Visible = false;
					}
					if (articlesGrid.Columns.Contains("li_intitule"))
					{
						articlesGrid.Columns["li_intitule"].Visible = false;
					}
					if (articlesGrid.Columns.Contains("LI_Complement"))
					{
						articlesGrid.Columns["LI_Complement"].Visible = false;
					}
					if (articlesGrid.Columns.Contains("veepee_product_id"))
					{
						articlesGrid.Columns["veepee_product_id"].Visible = false;
					}
					if (articlesGrid.Columns.Contains("LI_Pallet"))
					{
						articlesGrid.Columns["LI_Pallet"].Visible = true;
					}
					lblPe.Text = "ESCANEAR ARTÍCULO";
					panelScanPe.BackColor = default(Color);
					for (int x = 0; x < articlesGrid.Rows.Count; x++)
					{
						articlesTotal += Convert.ToDouble(articlesGrid.Rows[x].Cells["QTY"].Value.ToString());
						articlesLeido += Convert.ToDouble(articlesGrid.Rows[x].Cells["Leido"].Value.ToString());
						paintTable(x);
						if (x == 0)
						{
							lastRowValue = articlesGrid.Rows[x].Cells["PE"].Value.ToString();
							peList.Add(lastRowValue);
						}
						else
						{
							lastRowValue = articlesGrid.Rows[x - 1].Cells["PE"].Value.ToString();
						}
						if (!articlesGrid.Rows[x].Cells["PE"].Value.ToString().Equals(lastRowValue))
						{
							peList.Add(articlesGrid.Rows[x].Cells["PE"].Value.ToString());
						}
					}
					seqValueLbl.Text = peList.Count().ToString();
					recoverLastPackingListLines();
				}
				else
				{
					resetFormOnDbChange();
					panelScanPe.Visible = false;
					panelTable.Visible = false;
					progressBarTotal.Visible = false;
					MessageBox.Show("El archivo de Logs esta vacío.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("recoverLastLines_ " + ex.Message, "Error");
			}
		}

		private void recoverLastPackingListLines()
		{
			try
			{
				string logFileName = "packing_list_" + company + ".txt";
				string logFilePathName = Path.Combine(logFolderPath, logFileName);
				if (!File.Exists(logFilePathName))
				{
					MessageBox.Show("No hay logs de packing list", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					return;
				}
				string[] lines = File.ReadAllLines(logFilePathName);
				if (lines.Length != 0)
				{
					for (int i = 0; i < lines.Count(); i++)
					{
						DataRow dRow = packingListDt.NewRow();
						string[] values = lines[i].Split(';');
						for (int j = 0; j < values.Count() && j < packingListDt.Columns.Count; j++)
						{
							dRow[j] = values[j];
						}
						packingListDt.Rows.Add(dRow);
					}
				}
				else
				{
					MessageBox.Show("Packing list esta vacío", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("recoverLastPackingListLines_" + ex.Message, "Error");
			}
		}

		private void newBoxTxt_KeyDown(object sender, KeyEventArgs e)
		{
			try
			{
				if (e.KeyCode == Keys.Escape)
				{
					e.SuppressKeyPress = true;
				}
				else if (e.KeyCode == Keys.Return)
				{
					e.SuppressKeyPress = true;
					string input = newBoxTxt.Text.Trim();
					changeBox(input, increment: true);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("newBoxTxt_KeyDown_ " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void changeBox(string seqInput, bool increment)
		{
			bool isValidBox = false;
			int currentQty = 0;
			int totalQtyPe = 0;
			string seq = "";
			string pe = "";
			string box = "";
			if (seqInput.Length == seqLength && !acceptPe)
			{
				foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
				{
					if (row.Cells["SEQ"].Value.ToString().Equals(seqInput) && !Convert.ToBoolean(row.Cells["Finalizado"].Value.ToString()))
					{
						currentQty += Convert.ToInt32(row.Cells["Leido"].Value.ToString());
						totalQtyPe += Convert.ToInt32(row.Cells["QTY"].Value.ToString());
						seq = row.Cells["SEQ"].Value.ToString();
						pe = row.Cells["PE"].Value.ToString();
						box = row.Cells["Caja"].Value.ToString();
						isValidBox = true;
					}
				}
				if ((from row3 in packingListDt.AsEnumerable()
					where row3["PE"].ToString().Equals(pe)
					where row3["BOX"].ToString().Equals(box)
					select row3.Field<int>("QTY")).Sum() > 0 && currentQty > 0 && currentQty < totalQtyPe && isValidBox)
				{
					(string, string) clientData = (string.Empty, string.Empty);
					DataTable tempClient = FetchClientInfoFromLivraison(company, pe);
					clientData = (tempClient.Rows[0]["Name"].ToString(), tempClient.Rows[0]["Pays"].ToString());
					if (clientData.Item1 == string.Empty && pe.Contains("/INT"))
					{
						clientData = (FetchLocationName(company, pe), "");
					}
					string matricula = string.Empty;
					if (clientData.Item1 != string.Empty && MatriculaActiva && increment && !CerrarCajaEnOdoo(seq, pe, box, out matricula))
					{
						// Modo matricula: Odoo no ha cerrado la caja; sigue abierta y el error ya se ha mostrado
					}
					else if (clientData.Item1 != string.Empty)
					{
						if (increment)
						{
							foreach (DataGridViewRow row2 in (IEnumerable)articlesGrid.Rows)
							{
								if (row2.Cells["SEQ"].Value.ToString().Equals(seqInput))
								{
									row2.Cells["Caja"].Value = Convert.ToInt32(row2.Cells["Caja"].Value.ToString()) + 1;
								}
							}
							logArticleLines();
							sound_ok.Play();
							lblPe.Text = "CAJA CAMBIADA \nESCANEAR ARTÍCULO";
							panelScanPe.BackColor = Color.LightGreen;
						}
						string origin = string.Empty;
						if (company.Equals("EFFE"))
						{
							origin = tempClient.Rows[0]["Origin"].ToString();
						}
						GenerateLabel(seq, pe, box, clientData.Item1, clientData.Item2, last: false, origin, matricula);
					}
					else
					{
						sound_error.Play();
						lblPe.Text = "ERROR: Problema con el cliente";
						panelScanPe.BackColor = Color.Red;
					}
				}
				else if (MatriculaActiva && isValidBox && increment && totalQtyPe > 0 && currentQty == totalQtyPe)
				{
					// Modo matricula: pedido completo cuya ultima caja no se pudo cerrar en Odoo; se reintenta
					CheckIfPeIsFinishedAndDoStuff(pe);
				}
				else if (!isValidBox)
				{
					sound_error.Play();
					lblPe.Text = "ERROR: SEQ no válida";
					panelScanPe.BackColor = Color.Red;
				}
				else
				{
					sound_error.Play();
					lblPe.Text = "ERROR: Caja vacía";
					panelScanPe.BackColor = Color.Red;
				}
			}
			nextBoxBtn.BackColor = default(Color);
			newBoxTxt.Enabled = false;
			newBoxTxt.Text = null;
			scanInput.Text = null;
			scanInput.Select();
		}

		private void nextBoxBtn_Click(object sender, EventArgs e)
		{
			if (articlesGrid.Rows.Count > 0 && articlesGrid.Columns.Count > 0 && !acceptPe)
			{
				lblPe.Text = "ESCANEAR CAJA A CAMBIAR";
				nextBoxBtn.BackColor = SystemColors.ButtonShadow;
				buttonClicked = true;
				newBoxTxt.Enabled = true;
				newBoxTxt.Text = null;
				newBoxTxt.Select();
			}
		}

		private void NathRecuperar_Click(object sender, EventArgs e)
		{
			try
			{
				if (MessageBox.Show("Cargar último pedido?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					db = companyIds["NATH"];
					company = "NATH";
					UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
					recoverLastLines();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private void AlanRecuperar_Click(object sender, EventArgs e)
		{
			try
			{
				if (MessageBox.Show("Cargar último pedido?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					db = companyIds["ALAN"];
					company = "ALAN";
					UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
					recoverLastLines();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private void CodeRecuperar_Click(object sender, EventArgs e)
		{
			try
			{
				if (MessageBox.Show("Cargar último pedido?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					db = companyIds["CODE"];
					company = "CODE";
					UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
					recoverLastLines();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private void TcnRecuperar_Click(object sender, EventArgs e)
		{
			try
			{
				if (MessageBox.Show("Cargar último pedido?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					db = companyIds["TCN"];
					company = "TCN";
					UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
					recoverLastLines();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private void TtucRecuperar_Click(object sender, EventArgs e)
		{
			try
			{
				if (MessageBox.Show("Cargar último pedido?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					db = companyIds["TTUC"];
					company = "TTUC";
					UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
					recoverLastLines();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private void EffectiveRecuperar_Click(object sender, EventArgs e)
		{
			try
			{
				if (MessageBox.Show("Cargar último pedido?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					db = companyIds["EFFE"];
					company = "EFFE";
					UncheckOtherToolStripMenuItems((ToolStripMenuItem)sender);
					recoverLastLines();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		public void UncheckOtherToolStripMenuItems(ToolStripMenuItem selectedMenuItem)
		{
			selectedMenuItem.Checked = true;
			foreach (ToolStripMenuItem item in from object item in selectedMenuItem.Owner.Items
				let ltoolStripMenuItem = item as ToolStripMenuItem
				where ltoolStripMenuItem != null
				where !item.Equals(selectedMenuItem)
				select ltoolStripMenuItem)
			{
				item.Checked = false;
			}
		}

		private void InitialForm_FormClosing(object sender, FormClosingEventArgs e)
		{
			if (AnyPendingArticles() && MessageBox.Show("Hay articulos por escanear, seguro?", "Confirmar", MessageBoxButtons.YesNo, MessageBoxIcon.Exclamation) == DialogResult.No)
			{
				e.Cancel = true;
			}
		}

		private void enviarEmailsToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				if (ReturnSetting("enviar").Equals("false"))
				{
					AddUpdateAppSettings("enviar", "true");
					enviarEmailsToolStripMenuItem.Checked = true;
					sendEmails = true;
				}
				else
				{
					AddUpdateAppSettings("enviar", "false");
					enviarEmailsToolStripMenuItem.Checked = false;
					sendEmails = false;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		public static string ReturnSetting(string key)
		{
			try
			{
				return ConfigurationManager.AppSettings[key] ?? "Not Found";
			}
			catch (ConfigurationErrorsException)
			{
				Console.WriteLine("Error reading app settings");
				return null;
			}
		}

		public static void AddUpdateAppSettings(string key, string value)
		{
			try
			{
				Configuration configuration = ConfigurationManager.OpenExeConfiguration(ConfigurationUserLevel.None);
				KeyValueConfigurationCollection settings = configuration.AppSettings.Settings;
				if (settings[key] == null)
				{
					settings.Add(key, value);
				}
				else
				{
					settings[key].Value = value;
				}
				configuration.Save(ConfigurationSaveMode.Modified);
				ConfigurationManager.RefreshSection(configuration.AppSettings.SectionInformation.Name);
			}
			catch (ConfigurationErrorsException)
			{
				Console.WriteLine("Error al guardar la configuración");
			}
		}

		private void CheckOrUncheckOptionMenu()
		{
			try
			{
				if (ReturnSetting("enviar").Equals("false"))
				{
					enviarEmailsToolStripMenuItem.Checked = false;
					sendEmails = false;
				}
				else
				{
					enviarEmailsToolStripMenuItem.Checked = true;
					sendEmails = true;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void CheckOrUncheckOptionMenu(string setting, ToolStripMenuItem toolStripMenuItem, bool value)
		{
			try
			{
				if (ReturnSetting(setting).Equals("false"))
				{
					toolStripMenuItem.Checked = false;
					value = false;
				}
				else
				{
					toolStripMenuItem.Checked = true;
					value = true;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void articlesGrid_ColumnAdded(object sender, DataGridViewColumnEventArgs e)
		{
			e.Column.SortMode = DataGridViewColumnSortMode.NotSortable;
		}

		private void pendingArticlesBtn_Click(object sender, EventArgs e)
		{
			if (AnyPendingArticles())
			{
				if (MessageBox.Show("Generar PDF con artículos pendientes?", "Generar PDF", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					ExportPendingArticlesToPDF(articlesGrid, print: false, question: true);
				}
			}
			else
			{
				MessageBox.Show("No hay artículos pendientes");
			}
			scanInput.Text = null;
			scanInput.Select();
		}

		private void ExportPendingArticlesToPDF(DataGridView dgw, bool print, bool question)
		{
			ArrayList duplicateList = new ArrayList();
			DataTable uniqueList = new DataTable();
			uniqueList.Columns.Add("STYLE");
			uniqueList.Columns.Add("COLOR");
			uniqueList.Columns.Add("SIZE");
			uniqueList.Columns.Add("QTY", typeof(double));
			uniqueList.Columns.Add("EAN_Code");
			uniqueList.PrimaryKey = new DataColumn[1] { uniqueList.Columns["EAN_Code"] };
			double pendientesQty = 0.0;
			try
			{
				Document doc = new Document(PageSize.A4, 30f, 30f, 25f, 25f);
				MemoryStream memStream = new MemoryStream();
				PdfWriter writer = PdfWriter.GetInstance(doc, memStream);
				doc.Open();
				PdfContentByte cb = writer.DirectContent;
				BarcodeEAN codeEan = new BarcodeEAN();
				BaseFont bf = BaseFont.CreateFont("Helvetica", "Cp1252", embedded: true);
				iTextSharp.text.Font headerTitle = new iTextSharp.text.Font(bf, 16f, 1, new BaseColor(253, 104, 54));
				iTextSharp.text.Font headerText = new iTextSharp.text.Font(bf, 12f, 1);
				new iTextSharp.text.Font(bf, 10f, 0);
				new iTextSharp.text.Font(bf, 10f, 1);
				iTextSharp.text.Font tableHeaderText = new iTextSharp.text.Font(bf, 8f, 1);
				iTextSharp.text.Font tableText = new iTextSharp.text.Font(bf, 8f, 0);
				Paragraph headerTitleParagraph = new Paragraph();
				headerTitleParagraph.Alignment = 0;
				headerTitleParagraph.Add(new Phrase("EFFECTIVE LOGISTICS & PICKING SL", headerTitle));
				Paragraph headerTextParagraph = new Paragraph();
				headerTextParagraph.Alignment = 2;
				headerTextParagraph.Add(new Phrase("Artículos pendientes " + company + "\n oleada " + nombreOleada, headerText));
				Paragraph separatorParagraph = new Paragraph(new Chunk(new LineSeparator(0f, 100f, BaseColor.BLACK, 0, 1f)));
				Paragraph pdfTableTitle = new Paragraph(new Phrase("Art. Pendientes" + Environment.NewLine, headerText));
				if (dgw.Columns.Count > 0 && dgw.Rows.Count > 0)
				{
					DataTable temporalTable = new DataTable();
					PdfPTable pdftable = new PdfPTable(6);
					pdftable.DefaultCell.Padding = 3f;
					pdftable.WidthPercentage = 100f;
					float[] colWidthPercentagesProducts = new float[6] { 20f, 16f, 12f, 10f, 18f, 24f };
					pdftable.SetWidths(colWidthPercentagesProducts);
					pdftable.HorizontalAlignment = 0;
					pdftable.DefaultCell.BorderWidth = 0.2f;
					PdfPCell cell1 = new PdfPCell(new Phrase("STYLE", tableHeaderText));
					PdfPCell cell2 = new PdfPCell(new Phrase("COLOR", tableHeaderText));
					PdfPCell cell3 = new PdfPCell(new Phrase("SIZE", tableHeaderText));
					PdfPCell cell4 = new PdfPCell(new Phrase("QTY_Pend", tableHeaderText));
					PdfPCell cell5 = new PdfPCell(new Phrase("EAN_Code", tableHeaderText));
					PdfPCell cell6 = new PdfPCell(new Phrase("EAN_Barcode", tableHeaderText));
					cell1.BackgroundColor = new BaseColor(Color.LightGray);
					cell2.BackgroundColor = new BaseColor(Color.LightGray);
					cell3.BackgroundColor = new BaseColor(Color.LightGray);
					cell4.BackgroundColor = new BaseColor(Color.LightGray);
					cell5.BackgroundColor = new BaseColor(Color.LightGray);
					cell6.BackgroundColor = new BaseColor(Color.LightGray);
					pdftable.AddCell(cell1);
					pdftable.AddCell(cell2);
					pdftable.AddCell(cell3);
					pdftable.AddCell(cell4);
					pdftable.AddCell(cell5);
					pdftable.AddCell(cell6);
					temporalTable.Columns.Add("STYLE");
					temporalTable.Columns.Add("COLOR");
					temporalTable.Columns.Add("SIZE");
					temporalTable.Columns.Add("QTY", typeof(double));
					temporalTable.Columns.Add("EAN_Code");
					for (int i = 0; i < dgw.Rows.Count; i++)
					{
						if (Convert.ToDouble(dgw.Rows[i].Cells["QTY"].Value.ToString()) > Convert.ToDouble(dgw.Rows[i].Cells["Leido"].Value.ToString()) && !Convert.ToBoolean(dgw.Rows[i].Cells["Finalizado"].Value.ToString()))
						{
							DataRow row = temporalTable.NewRow();
							row["STYLE"] = dgw.Rows[i].Cells["STYLE"].Value.ToString();
							row["COLOR"] = dgw.Rows[i].Cells["COLOR"].Value.ToString();
							row["SIZE"] = dgw.Rows[i].Cells["SIZE"].Value.ToString();
							double qty = Convert.ToDouble(dgw.Rows[i].Cells["QTY"].Value) - Convert.ToDouble(dgw.Rows[i].Cells["Leido"].Value);
							row["QTY"] = qty;
							row["EAN_Code"] = dgw.Rows[i].Cells["EAN_Code"].Value.ToString();
							temporalTable.Rows.Add(row);
						}
					}
					foreach (DataRow tempRow in temporalTable.Rows)
					{
						if (tempRow["EAN_Code"].ToString().Length > 0)
						{
							if (uniqueList.Rows.Contains(tempRow["EAN_Code"]))
							{
								duplicateList.Add(tempRow);
								continue;
							}
							DataRow row = uniqueList.NewRow();
							row["STYLE"] = tempRow["STYLE"].ToString();
							row["COLOR"] = tempRow["COLOR"].ToString();
							row["SIZE"] = tempRow["SIZE"].ToString();
							row["QTY"] = Convert.ToDouble(tempRow["QTY"].ToString());
							row["EAN_Code"] = tempRow["EAN_Code"].ToString();
							uniqueList.Rows.Add(row);
						}
					}
					foreach (DataRow uniqueRow in uniqueList.Rows)
					{
						foreach (DataRow duplicateRow in duplicateList)
						{
							if (uniqueRow["EAN_Code"].Equals(duplicateRow["EAN_Code"]))
							{
								double qty2 = Convert.ToDouble(uniqueRow["QTY"].ToString()) + Convert.ToDouble(duplicateRow["QTY"].ToString());
								uniqueRow["QTY"] = qty2;
							}
						}
					}
					uniqueList.DefaultView.Sort = "[STYLE] ASC, [SIZE] ASC";
					uniqueList = uniqueList.DefaultView.ToTable();
					for (int j = 0; j < uniqueList.Rows.Count; j++)
					{
						for (int k = 0; k < uniqueList.Columns.Count; k++)
						{
							pdftable.AddCell(new Phrase(uniqueList.Rows[j][k].ToString(), tableText));
						}
						pendientesQty += Convert.ToDouble(uniqueList.Rows[j][3].ToString());
						codeEan.GenerateChecksum = true;
						codeEan.CodeType = 1;
						codeEan.Code = uniqueList.Rows[j]["EAN_Code"].ToString();
						codeEan.Font = null;
						if (uniqueList.Rows[j]["EAN_Code"].ToString().Length == 13)
						{
							iTextSharp.text.Image image = codeEan.CreateImageWithBarcode(cb, null, null);
							image.ScaleAbsolute(75f, 12f);
							PdfPCell pcell = new PdfPCell(image, fit: false);
							pcell.HorizontalAlignment = 1;
							pcell.PaddingBottom = 5f;
							pcell.PaddingTop = 5f;
							pcell.BorderWidth = 0.2f;
							pdftable.AddCell(pcell);
						}
						else
						{
							pdftable.AddCell(new Phrase("ERROR: NO EAN CODE", tableText));
						}
					}
					pdfTableTitle.Add(pdftable);
				}
				doc.Add(headerTitleParagraph);
				doc.Add(headerTextParagraph);
				doc.Add(separatorParagraph);
				doc.Add(new Chunk("\n", headerText));
				doc.Add(new Chunk("\n", headerText));
				doc.Add(pdfTableTitle);
				doc.Add(separatorParagraph);
				Paragraph totalParagraph = new Paragraph(new Phrase("Qty pendientes: " + pendientesQty, tableHeaderText));
				doc.Add(totalParagraph);
				doc.Close();
				byte[] pdfContent = memStream.ToArray();
				string pdfFilename = Path.Combine(pdfPath, "pendientes_" + company + "_oleada_" + nombreOleada + ".pdf");
				using (FileStream fileStream = File.Create(pdfFilename))
				{
					fileStream.Write(pdfContent, 0, pdfContent.Length);
				}
				if (print)
				{
					PrintPDF(ReturnSetting("imp_pack").ToString(), "A4", pdfFilename, 1);
					return;
				}
				Process process = new Process();
				process.StartInfo.FileName = "explorer";
				process.StartInfo.Arguments = "\"" + pdfFilename;
				process.Start();
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "");
			}
		}

		private void GeneratePackingListPDF(string pe, string client, string address, string complement, string codePostal, string ville, string codeRegion, string pays, string telephone, string email, int productQty, string box, string deliveryDate)
		{
			try
			{
				Document doc = new Document(PageSize.A4, 30f, 30f, 25f, 25f);
				MemoryStream memStream = new MemoryStream();
				PdfWriter.GetInstance(doc, memStream);
				string dbName = "";
				int totalBox = (from row2 in packingListDt.AsEnumerable()
					where row2["PE"].ToString().Equals(pe)
					select row2.Field<int>("BOX")).Distinct().Count();
				doc.Open();
				BaseFont bf = BaseFont.CreateFont("Helvetica", "Cp1252", embedded: true);
				iTextSharp.text.Font headerTitle = new iTextSharp.text.Font(bf, 16f, 1);
				iTextSharp.text.Font headerText = new iTextSharp.text.Font(bf, 12f, 1);
				new iTextSharp.text.Font(bf, 10f, 0);
				new iTextSharp.text.Font(bf, 10f, 1);
				iTextSharp.text.Font tableHeaderText = new iTextSharp.text.Font(bf, 8f, 1);
				iTextSharp.text.Font tableText = new iTextSharp.text.Font(bf, 8f, 0);
				Paragraph headerTitleParagraph = new Paragraph();
				headerTitleParagraph.Alignment = 0;
				PdfPCell logo = null;
				switch (company)
				{
				case "NATH":
					dbName = "NATH";
					logo = new PdfPCell(iTextSharp.text.Image.GetInstance(Resources.LOGO_NATH, ImageFormat.Png), fit: false);
					break;
				case "CODE":
					dbName = "CODE 22";
					logo = new PdfPCell(iTextSharp.text.Image.GetInstance(Resources.LOGO_CODE, ImageFormat.Png), fit: false);
					break;
				case "ALAN":
					dbName = "ORY";
					logo = new PdfPCell(iTextSharp.text.Image.GetInstance(Resources.LOGO_ORY, ImageFormat.Png), fit: false);
					break;
				case "TCN":
					dbName = "TCN";
					logo = new PdfPCell(iTextSharp.text.Image.GetInstance(Resources.LOGO_TCN, ImageFormat.Png), fit: false);
					break;
				case "TTUC":
					dbName = "TUC TUC";
					logo = new PdfPCell(iTextSharp.text.Image.GetInstance(Resources.LOGO_TUCTUC, ImageFormat.Png), fit: false);
					break;
				case "EFFE":
					dbName = "EFFECTIVE";
					logo = new PdfPCell(iTextSharp.text.Image.GetInstance(Resources.LOGO_NATH, ImageFormat.Png), fit: false);
					break;
				}
				logo.BorderWidth = 0f;
				logo.HorizontalAlignment = 1;
				logo.VerticalAlignment = 5;
				headerTitleParagraph.Add(new Phrase(dbName, headerTitle));
				Paragraph headerTextParagraph = new Paragraph();
				headerTextParagraph.Alignment = 2;
				headerTextParagraph.Add(new Phrase("PACKING LIST - INFORME REVISIÓN \n", headerText));
				Paragraph separatorParagraph = new Paragraph(new Chunk(new LineSeparator(0f, 100f, BaseColor.BLACK, 0, 1f)));
				Paragraph totalParagraph = new Paragraph(new Phrase("Total Quantity: " + productQty, tableHeaderText));
				Paragraph clientDataParagraph = new Paragraph();
				Paragraph pdfTableTitle = new Paragraph();
				PdfPTable table = new PdfPTable(2);
				table.DefaultCell.Padding = 3f;
				table.WidthPercentage = 100f;
				float[] colWidthPercentagesTable = new float[2] { 50f, 50f };
				table.SetWidths(colWidthPercentagesTable);
				table.HorizontalAlignment = 5;
				table.DefaultCell.BorderWidth = 0f;
				PdfPTable clientDataTable = new PdfPTable(2);
				clientDataTable.DefaultCell.Padding = 3f;
				clientDataTable.WidthPercentage = 50f;
				float[] colWidthPercentagesClientData = new float[2] { 15f, 35f };
				clientDataTable.SetWidths(colWidthPercentagesClientData);
				clientDataTable.HorizontalAlignment = 0;
				clientDataTable.DefaultCell.BorderWidth = 0.2f;
				PdfPCell header1 = new PdfPCell(new Phrase("Customer", tableHeaderText));
				PdfPCell header2 = new PdfPCell(new Phrase("Order", tableHeaderText));
				PdfPCell header3 = new PdfPCell(new Phrase("Date", tableHeaderText));
				PdfPCell header4 = new PdfPCell(new Phrase("Total Box", tableHeaderText));
				PdfPCell header5 = new PdfPCell(new Phrase("Total Qty", tableHeaderText));
				PdfPCell header6 = new PdfPCell(new Phrase("Address", tableHeaderText));
				PdfPCell name = new PdfPCell(new Phrase(client, tableText));
				PdfPCell order = new PdfPCell(new Phrase(pe, tableText));
				PdfPCell date = new PdfPCell(new Phrase(deliveryDate, tableText));
				PdfPCell totalBoxes = new PdfPCell(new Phrase(totalBox.ToString(), tableText));
				PdfPCell totalArticles = new PdfPCell(new Phrase(productQty.ToString(), tableText));
				PdfPCell addressData = new PdfPCell(new Phrase(client + "\n" + complement + "\n" + address + "\n" + codePostal + " - " + ville + "\n" + codeRegion + " - " + pays + "\n" + telephone + "\n" + email, tableText));
				clientDataTable.AddCell(header1);
				clientDataTable.AddCell(name);
				clientDataTable.AddCell(header2);
				clientDataTable.AddCell(order);
				clientDataTable.AddCell(header3);
				clientDataTable.AddCell(date);
				clientDataTable.AddCell(header4);
				clientDataTable.AddCell(totalBoxes);
				clientDataTable.AddCell(header5);
				clientDataTable.AddCell(totalArticles);
				clientDataTable.AddCell(header6);
				clientDataTable.AddCell(addressData);
				table.AddCell(clientDataTable);
				table.AddCell(logo);
				clientDataParagraph.Add(table);
				if (packingListDt.Columns.Count > 0 && packingListDt.Rows.Count > 0)
				{
					PdfPTable pdftable = new PdfPTable(6);
					pdftable.DefaultCell.Padding = 3f;
					pdftable.WidthPercentage = 100f;
					pdftable.HorizontalAlignment = 0;
					pdftable.DefaultCell.BorderWidth = 0.2f;
					PdfPCell cell1 = new PdfPCell(new Phrase("BOX", tableHeaderText));
					PdfPCell cell2 = new PdfPCell(new Phrase("STYLE", tableHeaderText));
					PdfPCell cell3 = new PdfPCell(new Phrase("COLOR", tableHeaderText));
					PdfPCell cell4 = new PdfPCell(new Phrase("SIZE", tableHeaderText));
					PdfPCell cell5 = new PdfPCell(new Phrase("EAN", tableHeaderText));
					PdfPCell cell6 = new PdfPCell(new Phrase("QTY", tableHeaderText));
					cell1.BackgroundColor = new BaseColor(Color.LightGray);
					cell2.BackgroundColor = new BaseColor(Color.LightGray);
					cell3.BackgroundColor = new BaseColor(Color.LightGray);
					cell4.BackgroundColor = new BaseColor(Color.LightGray);
					cell5.BackgroundColor = new BaseColor(Color.LightGray);
					cell6.BackgroundColor = new BaseColor(Color.LightGray);
					pdftable.AddCell(cell1);
					pdftable.AddCell(cell2);
					pdftable.AddCell(cell3);
					pdftable.AddCell(cell4);
					pdftable.AddCell(cell5);
					pdftable.AddCell(cell6);
					foreach (DataRow row in packingListDt.Rows)
					{
						if (row["PE"].ToString().Equals(pe))
						{
							pdftable.AddCell(new Phrase(row["BOX"].ToString(), tableText));
							pdftable.AddCell(new Phrase(row["STYLE"].ToString(), tableText));
							pdftable.AddCell(new Phrase(row["COLOR"].ToString(), tableText));
							pdftable.AddCell(new Phrase(row["SIZE"].ToString(), tableText));
							pdftable.AddCell(new Phrase(row["EAN"].ToString(), tableText));
							pdftable.AddCell(new Phrase(row["QTY"].ToString(), tableText));
						}
					}
					pdfTableTitle.Add(pdftable);
				}
				doc.Add(headerTitleParagraph);
				doc.Add(headerTextParagraph);
				doc.Add(separatorParagraph);
				doc.Add(new Chunk("\n", headerText));
				doc.Add(clientDataParagraph);
				doc.Add(new Chunk("\n", headerText));
				doc.Add(pdfTableTitle);
				doc.Add(separatorParagraph);
				doc.Add(totalParagraph);
				doc.Close();
				byte[] pdfContent = memStream.ToArray();
				string pedido = pe.Replace("/", "");
				string pdfFilename = Path.Combine(pdfPackingPath, "PKL_" + dbName + "_" + pedido + ".pdf");
				using (FileStream fileStream = File.Create(pdfFilename))
				{
					fileStream.Write(pdfContent, 0, pdfContent.Length);
				}
				if (printPacking)
				{
					PrintPDF(ReturnSetting("imp_pack").ToString(), "A4", pdfFilename, 1);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("GeneratePackingListPDF: " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		public bool PrintPDF(string printer, string paperName, string filename, int copies)
		{
			try
			{
				PrinterSettings printerSettings = new PrinterSettings
				{
					PrinterName = printer,
					Copies = (short)copies
				};
				PageSettings pageSettings = new PageSettings(printerSettings)
				{
					Margins = new Margins(0, 0, 0, 0)
				};
				foreach (PaperSize paperSize in printerSettings.PaperSizes)
				{
					if (paperSize.PaperName == paperName)
					{
						pageSettings.PaperSize = paperSize;
						break;
					}
				}
				using (PdfiumViewer.PdfDocument document = PdfiumViewer.PdfDocument.Load(filename))
				{
					using (PrintDocument printDocument = document.CreatePrintDocument(PdfPrintMode.ShrinkToMargin))
					{
						printDocument.PrinterSettings = printerSettings;
						printDocument.DefaultPageSettings = pageSettings;
						printDocument.PrintController = new StandardPrintController();
						printDocument.Print();
					}
				}
				return true;
			}
			catch
			{
				return false;
			}
		}

		private void _timer_Tick(object sender, EventArgs e)
		{
			TimeSpan timeSinceStartTime = DateTime.Now - _startTime;
			timeSinceStartTime = new TimeSpan(timeSinceStartTime.Hours, timeSinceStartTime.Minutes, timeSinceStartTime.Seconds);
			_currentElapsedTime = timeSinceStartTime + _totalElapsedTime;
			_totalElapsedTimeDisplay.Text = _currentElapsedTime.ToString();
			_shiftCurrentElapsedTime = timeSinceStartTime + _shiftTotalTime;
			_shiftTotalTimeDisplay.Text = "Jornada (h): " + _shiftCurrentElapsedTime.ToString();
			GetBatchProductivityRecords();
		}

		private void _pause_timer_Tick(object sender, EventArgs e)
		{
			TimeSpan pauseTime = DateTime.Now - _shiftPauseStartTime;
			pauseTime = new TimeSpan(pauseTime.Hours, pauseTime.Minutes, pauseTime.Seconds);
			_shiftCurrentPausedTime = pauseTime + _shiftTotalPausedTime;
			_shiftPausedTimeDisplay.Text = "Pausas (h): " + _shiftCurrentPausedTime.ToString();
		}

		private void pauseTimerBtn_Click(object sender, EventArgs e)
		{
			PauseTimer();
			PauseShiftTimer();
			StartPauseTimer();
		}

		private void PauseTimer()
		{
			if (_timerRunning)
			{
				_timer.Stop();
				_timerRunning = false;
			}
		}

		private void PauseShiftTimer()
		{
			if (_shiftTimerRunning)
			{
				_shiftTimer.Stop();
				_shiftTimerRunning = false;
			}
		}

		private void PausePauseTimer()
		{
			if (_shiftPauseTimerRunning)
			{
				_shiftPauseTimer.Stop();
				_shiftPauseTimerRunning = false;
			}
		}

		private void StartPauseTimer()
		{
			if (!_shiftPauseTimerRunning)
			{
				_shiftPauseStartTime = DateTime.Now;
				_shiftTotalPausedTime = _shiftCurrentPausedTime;
				_shiftPauseTimer.Start();
				_shiftPauseTimerRunning = true;
			}
		}

		private void StartShiftTimer()
		{
			if (!_shiftTimerRunning)
			{
				_shiftStartTime = DateTime.Now;
				_shiftTotalTime = _shiftCurrentElapsedTime;
				_shiftTimer.Start();
				_shiftTimerRunning = true;
			}
		}

		private void StartTimer()
		{
			if (!_timerRunning)
			{
				_startTime = DateTime.Now;
				_totalElapsedTime = _currentElapsedTime;
				_timer.Start();
				_timerRunning = true;
			}
		}

		private void resetTimer()
		{
			_timer.Stop();
			_timerRunning = false;
			_shiftTimer.Stop();
			_shiftTimerRunning = false;
			_shiftPauseTimer.Stop();
			_shiftPauseTimerRunning = false;
			_totalElapsedTime = TimeSpan.Zero;
			_currentElapsedTime = TimeSpan.Zero;
			_shiftTotalTime = TimeSpan.Zero;
			_shiftCurrentElapsedTime = TimeSpan.Zero;
			_shiftTotalPausedTime = TimeSpan.Zero;
			_shiftCurrentPausedTime = TimeSpan.Zero;
			_totalElapsedTimeDisplay.Text = _totalElapsedTime.ToString();
			_shiftTotalTimeDisplay.Text = "Jornada (h): " + _shiftTotalTime.ToString();
			_shiftPausedTimeDisplay.Text = "Pausas (h): " + _shiftTotalPausedTime.ToString();
		}

		private void productivityBtn_Click(object sender, EventArgs e)
		{
			if (MessageBox.Show("¿Finalizar jornada?", "Finalización jornada", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
			{
				PauseTimer();
				PauseShiftTimer();
				PausePauseTimer();
				if (crmLogs)
				{
					InsertProductivity();
				}
				FinishShift();
				lblPe.BackColor = Color.NavajoWhite;
				lblPe.Text = "JORNADA FINALIZADA";
			}
		}

		private void GetBatchProductivityRecords()
		{
			double hours = _currentElapsedTime.TotalHours;
			productivity = (articlesLeido - articleManual) / hours;
			productivity = Math.Round(productivity, 0, MidpointRounding.AwayFromZero);
			double timeRemaining = (articlesTotal - articlesLeido) / productivity;
			timeRemaining = Math.Round(timeRemaining, 1, MidpointRounding.AwayFromZero);
			totalUnitsHourLbl.Text = "Ritmo (U/h): " + productivity;
			timeRemainingLbl.Text = "Restante (h): " + timeRemaining;
			if (productivity < 100.0)
			{
				totalUnitsHourLbl.ForeColor = Color.Red;
			}
			double shiftHours = _shiftCurrentElapsedTime.TotalHours;
			shiftProductivity = shiftArticles / shiftHours;
			shiftProductivity = Math.Round(shiftProductivity, 0, MidpointRounding.AwayFromZero);
			shiftScansLabel.Text = "Unidades (turno): " + shiftArticles;
			shiftProductivityLabel.Text = "U/h (turno): " + shiftProductivity;
		}

		private void FinishShift()
		{
			shiftArticles = 0.0;
			shiftProductivity = 0.0;
			shiftScansLabel.Text = "Unidades (turno): " + shiftArticles;
			shiftProductivityLabel.Text = "U/h (turno): " + shiftProductivity;
			_shiftTotalTime = TimeSpan.Zero;
			_shiftCurrentElapsedTime = TimeSpan.Zero;
			_shiftTotalTimeDisplay.Text = "Jornada (h): " + _shiftTotalTime.ToString();
			_shiftTotalPausedTime = TimeSpan.Zero;
			_shiftCurrentPausedTime = TimeSpan.Zero;
			_shiftPausedTimeDisplay.Text = "Pausas (h): " + _shiftTotalPausedTime.ToString();
		}

		private void InsertProductivity()
		{
			if (modoPrueba)
			{
				LogPrueba("INSERT Productividad_Operadores no hecho: " + shiftArticles + " uds");
				return;
			}
			try
			{
				using (SqlConnection conn = new SqlConnection(crmConectionString))
				{
					conn.Open();
					SqlCommand sqlCommand = new SqlCommand(queryInsertProductivityRecords, conn);
					sqlCommand.Parameters.AddWithValue("@user_id", 1);
					sqlCommand.Parameters.AddWithValue("@articulos_jornada", shiftArticles);
					sqlCommand.Parameters.AddWithValue("@duracion_jornada", _shiftTotalTimeDisplay.Text.Substring(13, 8));
					sqlCommand.Parameters.AddWithValue("@duracion_pausas", _shiftPausedTimeDisplay.Text.Substring(12, 8));
					sqlCommand.Parameters.AddWithValue("@estacion_trabajo", SystemInformation.ComputerName);
					sqlCommand.ExecuteNonQuery();
				}
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("InsertProductivity_ " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes && crmLogs)
				{
					InsertProductivity();
				}
			}
		}

		private bool AnyPendingArticles()
		{
			bool arePending = false;
			if (articlesLeido < articlesTotal)
			{
				arePending = true;
			}
			return arePending;
		}

		public void GenerateLabel(string seq, string pe, string box, string clientName, string country, bool last, string origin, string matricula = "")
		{
			try
			{
				if (!printLabels)
				{
					return;
				}
				using (new Bitmap(100, 100))
				{
					StringBuilder sBuilder = new StringBuilder(25);
					if (clientName.Length > 25)
					{
						sBuilder.Append(clientName);
						sBuilder.Insert(25, "\n");
					}
					else
					{
						sBuilder.Append(clientName);
					}
					using (PrintDocument pd = new PrintDocument())
					{
						pd.PrintController = new StandardPrintController();
						pd.PrintPage += delegate(object printSender, PrintPageEventArgs printE)
						{
							System.Drawing.Font font = new System.Drawing.Font("Arial", 10f);
							System.Drawing.Font font2 = new System.Drawing.Font("Arial", 16f);
							System.Drawing.Font font3 = new System.Drawing.Font("Arial", 16f, FontStyle.Underline);
							System.Drawing.Font font4 = new System.Drawing.Font("Arial", 36f);
							System.Drawing.Font font5 = new System.Drawing.Font("Arial", 10f);
							printE.Graphics.DrawString(company, font, Brushes.Black, new PointF(95f, 5f));
							printE.Graphics.DrawString(seq, font4, Brushes.Black, new PointF(70f, 25f));
							printE.Graphics.DrawString(pe, font2, Brushes.Black, new PointF(20f, 80f));
							BarcodeLib.Barcode barcode = new BarcodeLib.Barcode();
							System.Drawing.Image image = barcode.Encode(TYPE.CODE128, pe, Color.Black, Color.White, 225, 50);
							printE.Graphics.DrawImage(image, 0, 125);
							printE.Graphics.DrawString(sBuilder.ToString(), font5, Brushes.Black, new PointF(0f, 185f));
							printE.Graphics.DrawString("BOX", font3, Brushes.Black, new PointF(85f, 225f));
							if (last)
							{
								int num = (from row in packingListDt.AsEnumerable()
									where row["PE"].ToString().Equals(pe)
									select row.Field<int>("BOX")).Distinct().Count();
								printE.Graphics.DrawString(box + "/" + num, font4, Brushes.Black, new PointF(75f, 250f));
							}
							else
							{
								printE.Graphics.DrawString(box, font4, Brushes.Black, new PointF(85f, 250f));
							}
							printE.Graphics.DrawString(country, font5, Brushes.Black, new PointF(85f, 300f));
							if (origin.Length > 0)
							{
								printE.Graphics.DrawString(origin, font5, Brushes.Black, new PointF(20f, 315f));
								System.Drawing.Image image2 = barcode.Encode(TYPE.CODE128, origin, Color.Black, Color.White, 225, 50);
								printE.Graphics.DrawImage(image2, 0, 330);
							}
							if (!string.IsNullOrEmpty(matricula))
							{
								// Modo matricula KOROSHI: matricula de la caja (paquete en Odoo)
								printE.Graphics.DrawString(matricula, font2, Brushes.Black, new PointF(20f, 385f));
								System.Drawing.Image image3 = barcode.Encode(TYPE.CODE128, matricula, Color.Black, Color.White, 225, 50);
								printE.Graphics.DrawImage(image3, 0, 412);
							}
						};
						pd.PrinterSettings.PrinterName = ReturnSetting("imp_tick").ToString();
						pd.Print();
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private DataTable FetchClientInfoFromLivraison(string database, string peCode)
		{
			try
			{
				DataTable clientInfo = new DataTable();
				clientInfo.Columns.Add("Name");
				clientInfo.Columns.Add("Address");
				clientInfo.Columns.Add("Complement");
				clientInfo.Columns.Add("CodePostal");
				clientInfo.Columns.Add("Ville");
				clientInfo.Columns.Add("CodeRegion");
				clientInfo.Columns.Add("Pays");
				clientInfo.Columns.Add("Telephone");
				clientInfo.Columns.Add("Email");
				clientInfo.Columns.Add("DeliveryDate");
				clientInfo.Columns.Add("Origin");
				clientInfo.Columns.Add("Remarks");
				clientInfo.Columns.Add("CountryCode");
				clientInfo.Columns.Add("EciDelivery");
				clientInfo.Columns.Add("ProvinceCode");
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryGetClientData, cSql.dbConn);
					npgsqlCommand.Parameters.AddWithValue("@order", peCode);
					if (company.Equals("TTUC"))
					{
						if (peCode.StartsWith("W_CAD"))
						{
							db = companyIds["TTUC_CAD"];
						}
						else if (peCode.StartsWith("W_COP"))
						{
							db = companyIds["TTUC_COP"];
						}
						else if (peCode.StartsWith("W_USA"))
						{
							db = companyIds["TTUC_USA"];
						}
					}
					if (company.Equals("ALAN") && peCode.StartsWith("CAREY"))
					{
						db = companyIds["CAREY"];
					}
					npgsqlCommand.Parameters.AddWithValue("@company_id", db);
					NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
					if (reader.HasRows)
					{
						reader.Read();
						clientInfo.Rows.Add(reader["name"].ToString(), reader["address"].ToString(), reader["complement"].ToString(), reader["codepostal"].ToString(), reader["ville"].ToString(), reader["coderegion"].ToString(), reader["pays"].ToString(), reader["telephone"].ToString(), reader["email"].ToString(), reader["deliverydate"].ToString(), reader["origin"].ToString(), reader["remarks"].ToString(), reader["country_code"].ToString(), reader["shipping_type_label"].ToString(), reader["province_code"].ToString());
						reader.Close();
					}
					cSql.dbConn.Close();
				}
				return clientInfo;
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("FetchClientInfoFromLivraison: " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes)
				{
					FetchClientInfoFromLivraison(database, peCode);
				}
				return null;
			}
		}

		private string FetchLocationName(string database, string order)
		{
			try
			{
				string locationName = string.Empty;
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryGetLocationBarcode, cSql.dbConn);
					npgsqlCommand.Parameters.AddWithValue("@order", order);
					if (company.Equals("TTUC"))
					{
						if (order.StartsWith("W_CAD"))
						{
							db = companyIds["TTUC_CAD"];
						}
						else if (order.StartsWith("W_COP"))
						{
							db = companyIds["TTUC_COP"];
						}
						else if (order.StartsWith("W_USA"))
						{
							db = companyIds["TTUC_USA"];
						}
					}
					if (company.Equals("ALAN") && order.StartsWith("CAREY"))
					{
						db = companyIds["CAREY"];
					}
					npgsqlCommand.Parameters.AddWithValue("@company_id", db);
					NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
					if (reader.HasRows)
					{
						reader.Read();
						locationName = reader["barcode"].ToString();
						reader.Close();
					}
					cSql.dbConn.Close();
				}
				return locationName;
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("FetchLocationName: " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes)
				{
					FetchLocationName(database, order);
				}
				return null;
			}
		}

		public static bool IsValidGtin(string code)
		{
			if (!_gtinRegex.IsMatch(code))
			{
				return false;
			}
			code = code.PadLeft(14, '0');
			return code.Select((char c, int i) => (c - 48) * ((i % 2 != 0) ? 1 : 3)).Sum() % 10 == 0;
		}

		private void filtroPendBtn_Click(object sender, EventArgs e)
		{
			try
			{
				if (!buttonClicked)
				{
					foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
					{
						if (row.Cells["QTY"].Value.ToString().Equals(row.Cells["Leido"].Value.ToString()) || Convert.ToBoolean(row.Cells["Finalizado"].Value.ToString()))
						{
							articlesGrid.CurrentCell = null;
							articlesGrid.SuspendLayout();
							row.Visible = false;
							articlesGrid.ResumeLayout();
						}
					}
					buttonClicked = true;
					filtroPendBtn.BackColor = SystemColors.ButtonShadow;
				}
				else
				{
					foreach (DataGridViewRow row2 in (IEnumerable)articlesGrid.Rows)
					{
						if (row2.Cells["QTY"].Value.ToString().Equals(row2.Cells["Leido"].Value.ToString()) || Convert.ToBoolean(row2.Cells["Finalizado"].Value.ToString()))
						{
							articlesGrid.CurrentCell = null;
							articlesGrid.SuspendLayout();
							row2.Visible = true;
							articlesGrid.ResumeLayout();
						}
					}
					buttonClicked = false;
					filtroPendBtn.BackColor = SystemColors.ControlLight;
				}
				scanInput.Text = null;
				scanInput.Select();
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		public void NotifyParentForm(string pe, string style, string size, string color, string prodCode, string leidoManual, int index)
		{
			try
			{
				string box = "";
				string ean = "";
				string sml_id = "";
				int leido = 0;
				if (articlesGrid.Rows[index].Cells["PE"].Value.ToString().Equals(pe) && articlesGrid.Rows[index].Cells["Style"].Value.ToString().Equals(style) && articlesGrid.Rows[index].Cells["SIZE"].Value.ToString().Equals(size) && articlesGrid.Rows[index].Cells["COLOR"].Value.ToString().Equals(color) && articlesGrid.Rows[index].Cells["Product_code"].Value.ToString().Equals(prodCode))
				{
					articlesGrid.Rows[index].Cells["Leido"].Value = Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value.ToString()) + Convert.ToInt32(leidoManual);
					box = articlesGrid.Rows[index].Cells["Caja"].Value.ToString();
					ean = articlesGrid.Rows[index].Cells["EAN_Code"].Value.ToString();
					sml_id = articlesGrid.Rows[index].Cells["sml_id"].Value.ToString();
					leido = Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value);
				}
				articlesLeido += Convert.ToDouble(leidoManual);
				articleManual += Convert.ToDouble(leidoManual);
				lblPe.Text = "CONFIRMADO";
				panelScanPe.BackColor = Color.LightGreen;
				sound_ok.Play();
				scanInput.Text = null;
				scanInput.Select();
				UpdateProgressBar();
				logArticleLines();
				paintTable(rowOnDoubleClick);
				AddScanToPackingList(pe, Convert.ToInt32(box), style, color, size, ean, Convert.ToInt32(leidoManual));
				logPackingList();
				UpdateDoneQtyByOrderNumber(pe, leido, prodCode, ean, Convert.ToInt32(sml_id));
				CheckIfPeIsFinishedAndDoStuff(pe);
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void articlesGrid_CellDoubleClick(object sender, DataGridViewCellEventArgs e)
		{
			try
			{
				if (acceptPe)
				{
					return;
				}
				rowOnDoubleClick = e.RowIndex;
				if (articlesGrid != null && Convert.ToInt32(articlesGrid.Rows[e.RowIndex].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[e.RowIndex].Cells["Leido"].Value.ToString()))
				{
					string pe = articlesGrid.Rows[e.RowIndex].Cells["PE"].Value.ToString();
					string referencia = articlesGrid.Rows[e.RowIndex].Cells["Style"].Value.ToString();
					string size = articlesGrid.Rows[e.RowIndex].Cells["SIZE"].Value.ToString();
					string colour = articlesGrid.Rows[e.RowIndex].Cells["COLOR"].Value.ToString();
					string pCode = articlesGrid.Rows[e.RowIndex].Cells["Product_code"].Value.ToString();
					string qtyEsperada = articlesGrid.Rows[e.RowIndex].Cells["QTY"].Value.ToString();
					string qtyLeida = articlesGrid.Rows[e.RowIndex].Cells["Leido"].Value.ToString();
					using (Form1 frm1 = new Form1(pe, referencia, size, colour, pCode, qtyEsperada, qtyLeida, e.RowIndex))
					{
						frm1.ShowDialog(this);
						return;
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void InsertRecordsIntoCrmDatabase(HashSet<string> list)
		{
			if (modoPrueba)
			{
				LogPrueba("INSERT OrderPrintLog no hecho: " + peList.Count + " pedidos");
				return;
			}
			try
			{
				string companyName = "";
				string companyOrderId = "";
				if (peList.Count <= 0)
				{
					return;
				}
				foreach (string item in peList)
				{
					if (item.Length > 0 && (item.Contains("/OUT/") || item.Contains("/INT")))
					{
						switch (company)
						{
						case "NATH":
							companyName = "NATH";
							companyOrderId = item;
							break;
						case "CODE":
							companyName = "CODE22";
							companyOrderId = item;
							break;
						case "ALAN":
							companyName = "ORY";
							companyOrderId = item;
							break;
						case "TCN":
							companyName = "GC";
							companyOrderId = item;
							break;
						case "TTUC":
							companyName = "TTUC";
							companyOrderId = item;
							break;
						case "EFFE":
							companyName = "EFFE";
							companyOrderId = item;
							break;
						}
						InsertOrderPrintLogCrm(item, companyName, companyOrderId);
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("InsertRecordsIntoCrmDatabase_ " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void InsertOrderPrintLogCrm(string orderId, string companyName, string companyOrderId)
		{
			if (modoPrueba)
			{
				LogPrueba("INSERT OrderPrintLog no hecho: " + orderId);
				return;
			}
			try
			{
				using (SqlConnection conn = new SqlConnection(crmConectionString))
				{
					conn.Open();
					SqlCommand sqlCommand = new SqlCommand(insertOrderPrintLogCrmQuery, conn);
					sqlCommand.Parameters.AddWithValue("@orderId", orderId);
					sqlCommand.Parameters.AddWithValue("@companyName", companyName);
					sqlCommand.Parameters.AddWithValue("@companyOrderId", companyOrderId);
					sqlCommand.ExecuteNonQuery();
				}
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("InsertOrderPrintLogCrm_ " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes)
				{
					InsertOrderPrintLogCrm(orderId, companyName, companyOrderId);
				}
			}
		}

		private void InsertOrderDoubleCheckingLogCrm(string pe)
		{
			if (modoPrueba)
			{
				LogPrueba("INSERT OrderDoubleCheckingLog no hecho: " + pe);
				return;
			}
			try
			{
				string companyName = "";
				string companyOrderId = "";
				if (pe.Length > 0 && (pe.Contains("/OUT/") || pe.Contains("/INT")))
				{
					switch (company)
					{
					case "NATH":
						companyName = "NATH";
						companyOrderId = pe;
						break;
					case "CODE":
						companyName = "CODE22";
						companyOrderId = pe;
						break;
					case "ALAN":
						companyName = "ORY";
						companyOrderId = pe;
						break;
					case "TCN":
						companyName = "GC";
						companyOrderId = pe;
						break;
					case "TTUC":
						companyName = "TTUC";
						companyOrderId = pe;
						break;
					case "EFFE":
						companyName = "EFFE";
						companyOrderId = pe;
						break;
					}
					using (SqlConnection conn = new SqlConnection(crmConectionString))
					{
						conn.Open();
						SqlCommand sqlCommand = new SqlCommand(insertOrderDoubleCheckingLogQuery, conn);
						sqlCommand.Parameters.AddWithValue("@orderId", pe);
						sqlCommand.Parameters.AddWithValue("@companyName", companyName);
						sqlCommand.Parameters.AddWithValue("@companyOrderId", companyOrderId);
						sqlCommand.ExecuteNonQuery();
						return;
					}
				}
			}
			catch (Exception ex)
			{
				if (MessageBox.Show("InsertOrderDoubleCheckingLogCrm_ " + ex.Message, "Error", MessageBoxButtons.YesNo, MessageBoxIcon.Hand) == DialogResult.Yes)
				{
					InsertOrderDoubleCheckingLogCrm(pe);
				}
			}
		}

		private void UpdateBultosPedidoSage(string pe, int bultos)
		{
		}

		private string ReturnPeDeliveryDate(string scannedInput)
		{
			string date = "";
			try
			{
				if (scannedInput.Contains("/OUT/") || scannedInput.Contains("/INT"))
				{
					using (ConnectionSQL cSql = new ConnectionSQL(company))
					{
						cSql.dbConn.Open();
						NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryPeDateLivr, cSql.dbConn);
						npgsqlCommand.Parameters.AddWithValue("@input", scannedInput.ToString());
						NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
						if (reader.HasRows)
						{
							reader.Read();
							if (DateTime.TryParse(reader["DO_DateLivr"].ToString(), out var peDate))
							{
								peDate = Convert.ToDateTime(reader[0].ToString());
								date = $"{peDate:dd/MM/yyyy}";
							}
							reader.Close();
						}
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("ReturnPeDate_ " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return date;
		}

		private string ReturnPeCreationDate(string scannedInput)
		{
			string date = "";
			try
			{
				if (scannedInput.Contains("/OUT/") || scannedInput.Contains("/INT"))
				{
					using (ConnectionSQL cSql = new ConnectionSQL(company))
					{
						cSql.dbConn.Open();
						NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryPeDoDate, cSql.dbConn);
						npgsqlCommand.Parameters.AddWithValue("@input", scannedInput.ToString());
						NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
						if (reader.HasRows)
						{
							reader.Read();
							if (DateTime.TryParse(reader["DO_Date"].ToString(), out var peDate))
							{
								peDate = Convert.ToDateTime(reader[0].ToString());
								date = $"{peDate:dd/MM/yyyy}";
							}
							reader.Close();
						}
					}
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("ReturnPeCreationDate_ " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
			return date;
		}

		private void nombreOleadaTxt_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
			}
			else if (e.KeyCode == Keys.Return)
			{
				e.SuppressKeyPress = true;
				nombreOleada = nombreOleadaTxt.Text.Trim();
				char[] array = chars_to_replace;
				foreach (char element in array)
				{
					nombreOleada = nombreOleada.Replace(element, '-');
				}
				if (nombreOleada == "" || nombreOleada == null)
				{
					MessageBox.Show("Introduce un nombre de oleada válido", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					nombreOleadaTxt.Clear();
					return;
				}
				nombreOleadaLbl.Text = "Oleada: " + nombreOleada;
				nombreOleadaTxt.Clear();
				nombreOleadaTxt.Enabled = false;
				scanInput.Select();
			}
		}

		private void pendientesPedidoBox_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
			}
			else if (e.KeyCode == Keys.Return)
			{
				e.SuppressKeyPress = true;
				string seqPedidoPendientes = pendientesPedidoBox.Text.Trim();
				if (seqPedidoPendientes == "" || seqPedidoPendientes == null || seqPedidoPendientes.Length > seqLength)
				{
					MessageBox.Show("Introduce un número de Pedido (SEQ) válido!", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					pendientesPedidoBox.Clear();
				}
				else
				{
					generatePendientesNumeroPedido(seqPedidoPendientes);
					pendientesPedidoBox.Clear();
					scanInput.Select();
				}
			}
		}

		private void generatePendientesNumeroPedido(string seqPedidoPendientes)
		{
			DataTable uniqueList = new DataTable();
			uniqueList.Columns.Add("STYLE");
			uniqueList.Columns.Add("COLOR");
			uniqueList.Columns.Add("SIZE");
			uniqueList.Columns.Add("QTY", typeof(double));
			uniqueList.Columns.Add("EAN_Code");
			uniqueList.PrimaryKey = new DataColumn[1] { uniqueList.Columns["EAN_Code"] };
			double pendientesQty = 0.0;
			string pedido = "";
			try
			{
				for (int i = 0; i < articlesGrid.Rows.Count; i++)
				{
					if (Convert.ToDouble(articlesGrid.Rows[i].Cells["QTY"].Value.ToString()) > Convert.ToDouble(articlesGrid.Rows[i].Cells["Leido"].Value.ToString()) && articlesGrid.Rows[i].Cells["SEQ"].Value.ToString().Equals(seqPedidoPendientes))
					{
						pedido = articlesGrid.Rows[i].Cells["PE"].Value.ToString();
						DataRow row = uniqueList.NewRow();
						row["STYLE"] = articlesGrid.Rows[i].Cells["STYLE"].Value.ToString();
						row["COLOR"] = articlesGrid.Rows[i].Cells["COLOR"].Value.ToString();
						row["SIZE"] = articlesGrid.Rows[i].Cells["SIZE"].Value.ToString();
						double qty = Convert.ToDouble(articlesGrid.Rows[i].Cells["QTY"].Value) - Convert.ToDouble(articlesGrid.Rows[i].Cells["Leido"].Value);
						row["QTY"] = qty;
						row["EAN_Code"] = articlesGrid.Rows[i].Cells["EAN_Code"].Value.ToString();
						uniqueList.Rows.Add(row);
					}
				}
				if (uniqueList.Rows.Count > 0)
				{
					if (MessageBox.Show("Generar PDF con artículos pendientes?", "Generar PDF", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
					{
						return;
					}
					Document doc = new Document(PageSize.A4, 30f, 30f, 25f, 25f);
					MemoryStream memStream = new MemoryStream();
					PdfWriter writer = PdfWriter.GetInstance(doc, memStream);
					doc.Open();
					PdfContentByte cb = writer.DirectContent;
					BarcodeEAN codeEan = new BarcodeEAN();
					BaseFont bf = BaseFont.CreateFont("Helvetica", "Cp1252", embedded: true);
					iTextSharp.text.Font headerTitle = new iTextSharp.text.Font(bf, 16f, 1, new BaseColor(253, 104, 54));
					iTextSharp.text.Font headerText = new iTextSharp.text.Font(bf, 12f, 1);
					new iTextSharp.text.Font(bf, 10f, 0);
					new iTextSharp.text.Font(bf, 10f, 1);
					iTextSharp.text.Font tableHeaderText = new iTextSharp.text.Font(bf, 8f, 1);
					iTextSharp.text.Font tableText = new iTextSharp.text.Font(bf, 8f, 0);
					Paragraph headerTitleParagraph = new Paragraph();
					headerTitleParagraph.Alignment = 0;
					headerTitleParagraph.Add(new Phrase("EFFECTIVE LOGISTICS & PICKING SL", headerTitle));
					Paragraph headerTextParagraph = new Paragraph();
					headerTextParagraph.Alignment = 2;
					headerTextParagraph.Add(new Phrase("Artículos pendientes \n oleada " + company + " pedido " + pedido, headerText));
					Paragraph separatorParagraph = new Paragraph(new Chunk(new LineSeparator(0f, 100f, BaseColor.BLACK, 0, 1f)));
					Paragraph pdfTableTitle = new Paragraph(new Phrase("Art. Pendientes Seq " + seqPedidoPendientes + " " + Environment.NewLine, headerText));
					if (articlesGrid.Columns.Count > 0 && articlesGrid.Rows.Count > 0)
					{
						PdfPTable pdftable = new PdfPTable(6);
						pdftable.DefaultCell.Padding = 3f;
						pdftable.WidthPercentage = 100f;
						float[] colWidthPercentagesProducts = new float[6] { 20f, 16f, 12f, 10f, 18f, 24f };
						pdftable.SetWidths(colWidthPercentagesProducts);
						pdftable.HorizontalAlignment = 0;
						pdftable.DefaultCell.BorderWidth = 0.2f;
						PdfPCell cell1 = new PdfPCell(new Phrase("STYLE", tableHeaderText));
						PdfPCell cell2 = new PdfPCell(new Phrase("COLOR", tableHeaderText));
						PdfPCell cell3 = new PdfPCell(new Phrase("SIZE", tableHeaderText));
						PdfPCell cell4 = new PdfPCell(new Phrase("QTY_Pend", tableHeaderText));
						PdfPCell cell5 = new PdfPCell(new Phrase("EAN_Code", tableHeaderText));
						PdfPCell cell6 = new PdfPCell(new Phrase("EAN_Barcode", tableHeaderText));
						cell1.BackgroundColor = new BaseColor(Color.LightGray);
						cell2.BackgroundColor = new BaseColor(Color.LightGray);
						cell3.BackgroundColor = new BaseColor(Color.LightGray);
						cell4.BackgroundColor = new BaseColor(Color.LightGray);
						cell5.BackgroundColor = new BaseColor(Color.LightGray);
						cell6.BackgroundColor = new BaseColor(Color.LightGray);
						pdftable.AddCell(cell1);
						pdftable.AddCell(cell2);
						pdftable.AddCell(cell3);
						pdftable.AddCell(cell4);
						pdftable.AddCell(cell5);
						pdftable.AddCell(cell6);
						uniqueList.DefaultView.Sort = "[STYLE] ASC, [SIZE] ASC";
						uniqueList = uniqueList.DefaultView.ToTable();
						for (int j = 0; j < uniqueList.Rows.Count; j++)
						{
							for (int k = 0; k < uniqueList.Columns.Count; k++)
							{
								pdftable.AddCell(new Phrase(uniqueList.Rows[j][k].ToString(), tableText));
							}
							pendientesQty += Convert.ToDouble(uniqueList.Rows[j][3].ToString());
							codeEan.GenerateChecksum = true;
							codeEan.CodeType = 1;
							codeEan.Code = uniqueList.Rows[j]["EAN_Code"].ToString();
							codeEan.Font = null;
							if (uniqueList.Rows[j]["EAN_Code"].ToString().Length == 13)
							{
								iTextSharp.text.Image image = codeEan.CreateImageWithBarcode(cb, null, null);
								image.ScaleAbsolute(75f, 12f);
								PdfPCell pcell = new PdfPCell(image, fit: false);
								pcell.HorizontalAlignment = 1;
								pcell.PaddingBottom = 5f;
								pcell.PaddingTop = 5f;
								pcell.BorderWidth = 0.2f;
								pdftable.AddCell(pcell);
							}
							else
							{
								pdftable.AddCell(new Phrase("ERROR: NO EAN CODE", tableText));
							}
						}
						pdfTableTitle.Add(pdftable);
					}
					doc.Add(headerTitleParagraph);
					doc.Add(headerTextParagraph);
					doc.Add(separatorParagraph);
					doc.Add(new Chunk("\n", headerText));
					doc.Add(new Chunk("\n", headerText));
					doc.Add(pdfTableTitle);
					doc.Add(separatorParagraph);
					Paragraph totalParagraph = new Paragraph(new Phrase("Qty pendientes: " + pendientesQty, tableHeaderText));
					doc.Add(totalParagraph);
					doc.Close();
					byte[] pdfContent = memStream.ToArray();
					pedido = pedido.Replace("/", "");
					string pdfFilename = Path.Combine(pdfPath, "pendientes_" + company + "_" + pedido + ".pdf");
					using (FileStream fileStream = File.Create(pdfFilename))
					{
						fileStream.Write(pdfContent, 0, pdfContent.Length);
					}
					Process process = new Process();
					process.StartInfo.FileName = "explorer";
					process.StartInfo.Arguments = "\"" + pdfFilename;
					process.Start();
				}
				else
				{
					MessageBox.Show("Este pedido no tiene articulos pendientes.", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private void CheckOrUncheckOptionMenuPackingPrint()
		{
			try
			{
				if (ReturnSetting("imprimirPacking").Equals("false"))
				{
					imprimirPackingToolStripMenuItem.Checked = false;
					printPacking = false;
				}
				else
				{
					imprimirPackingToolStripMenuItem.Checked = true;
					printPacking = true;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void imprimirPackingToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				if (ReturnSetting("imprimirPacking").Equals("false"))
				{
					AddUpdateAppSettings("imprimirPacking", "true");
					imprimirPackingToolStripMenuItem.Checked = true;
					printPacking = true;
				}
				else
				{
					AddUpdateAppSettings("imprimirPacking", "false");
					imprimirPackingToolStripMenuItem.Checked = false;
					printPacking = false;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void CheckOrUncheckOptionMenuLabelsPrint()
		{
			try
			{
				if (ReturnSetting("imprimirLabels").Equals("false"))
				{
					imprimirEtiquetasCajaToolStripMenuItem.Checked = true;
					printLabels = true;
				}
				else
				{
					imprimirEtiquetasCajaToolStripMenuItem.Checked = false;
					printLabels = false;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void imprimirEtiquetasCajaToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				if (ReturnSetting("imprimirLabels").Equals("false"))
				{
					AddUpdateAppSettings("imprimirLabels", "true");
					imprimirEtiquetasCajaToolStripMenuItem.Checked = true;
					printLabels = true;
				}
				else
				{
					AddUpdateAppSettings("imprimirLabels", "false");
					imprimirEtiquetasCajaToolStripMenuItem.Checked = false;
					printLabels = false;
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void modoECIToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				if (company == null || company == "")
				{
					MessageBox.Show("Selecciona una base de datos", "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
				else if (MessageBox.Show("Cambiar de modo?", "Cambiar modo", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					cambiarModo(sender);
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void ModoVPToolStripMenuItem1_Click(object sender, EventArgs e)
		{
			try
			{
				if (company == null || company == "")
				{
					MessageBox.Show("Selecciona una base de datos", "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
				else if (MessageBox.Show("Cambiar de modo?", "Cambiar modo VP", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					cambiarModo(sender);
				}
			}
			catch (Exception)
			{
				MessageBox.Show("Error al leer la configuración");
			}
		}

		private void cambiarModo(object sender)
		{
			if (modoPrueba)
			{
				MessageBox.Show("En modo prueba solo se puede usar el modo normal.", "Modo prueba", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				return;
			}
			if (sender.Equals(modoVPToolStripMenuItem))
			{
				if (ReturnSetting("modoVP").Equals("false") && !VPmode)
				{
					AddUpdateAppSettings("modoVP", "true");
					modeStatusLabel.Text = "Modo VP";
					VPmode = true;
					modoVPToolStripMenuItem.Checked = true;
					modoVPGroupBox.Visible = true;
					AddUpdateAppSettings("generarEtiquetas", "false");
					generarEtiquetasEnvioToolStripMenuItem.Checked = false;
					generateShipmentLabels = false;
					AddUpdateAppSettings("modoECI", "false");
					ECImode = false;
					modoECIToolStripMenuItem.Checked = false;
				}
				else if (ReturnSetting("modoVP").Equals("true") && VPmode)
				{
					AddUpdateAppSettings("modoVP", "false");
					modeStatusLabel.Text = "Modo normal";
					VPmode = false;
					modoVPToolStripMenuItem.Checked = false;
					modoVPGroupBox.Visible = false;
					AddUpdateAppSettings("generarEtiquetas", "false");
					generarEtiquetasEnvioToolStripMenuItem.Checked = false;
					generateShipmentLabels = false;
					AddUpdateAppSettings("modoECI", "false");
					ECImode = false;
					modoECIToolStripMenuItem.Checked = false;
				}
			}
			else if (sender.Equals(modoECIToolStripMenuItem))
			{
				if (ReturnSetting("modoECI").Equals("false") && !ECImode)
				{
					AddUpdateAppSettings("modoECI", "true");
					modeStatusLabel.Text = "Modo ECI";
					ECImode = true;
					modoECIToolStripMenuItem.Checked = true;
					AddUpdateAppSettings("generarEtiquetas", "false");
					generarEtiquetasEnvioToolStripMenuItem.Checked = false;
					generateShipmentLabels = false;
					AddUpdateAppSettings("modoVP", "false");
					VPmode = false;
					modoVPToolStripMenuItem.Checked = false;
					modoVPGroupBox.Visible = false;
				}
				else if (ReturnSetting("modoECI").Equals("true") && ECImode)
				{
					AddUpdateAppSettings("modoECI", "false");
					modeStatusLabel.Text = "Modo normal";
					ECImode = false;
					modoECIToolStripMenuItem.Checked = false;
					AddUpdateAppSettings("generarEtiquetas", "false");
					generarEtiquetasEnvioToolStripMenuItem.Checked = false;
					generateShipmentLabels = false;
					AddUpdateAppSettings("modoVP", "false");
					VPmode = false;
					modoVPToolStripMenuItem.Checked = false;
					modoVPGroupBox.Visible = false;
				}
			}
			else if (sender.Equals(generarEtiquetasEnvioToolStripMenuItem))
			{
				if (ReturnSetting("generarEtiquetas").Equals("false") && !generateShipmentLabels)
				{
					modeStatusLabel.Text = "Modo ETIQUETAS";
					AddUpdateAppSettings("generarEtiquetas", "true");
					generarEtiquetasEnvioToolStripMenuItem.Checked = true;
					generateShipmentLabels = true;
					AddUpdateAppSettings("modoECI", "false");
					ECImode = false;
					modoECIToolStripMenuItem.Checked = false;
					AddUpdateAppSettings("modoVP", "false");
					VPmode = false;
					modoVPToolStripMenuItem.Checked = false;
					modoVPGroupBox.Visible = false;
				}
				else if (ReturnSetting("generarEtiquetas").Equals("true") && generateShipmentLabels)
				{
					modeStatusLabel.Text = "Modo normal";
					AddUpdateAppSettings("generarEtiquetas", "false");
					generarEtiquetasEnvioToolStripMenuItem.Checked = false;
					generateShipmentLabels = false;
					AddUpdateAppSettings("modoECI", "false");
					ECImode = false;
					modoECIToolStripMenuItem.Checked = false;
					AddUpdateAppSettings("modoVP", "false");
					VPmode = false;
					modoVPToolStripMenuItem.Checked = false;
					modoVPGroupBox.Visible = false;
				}
			}
		}

		private void configuraciónToolStripMenuItem_Click(object sender, EventArgs e)
		{
			using (Configuracion conf = new Configuracion())
			{
				conf.ShowDialog(this);
			}
		}

		private void pklNoAcabadoTxt_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
			}
			else if (e.KeyCode == Keys.Return)
			{
				e.SuppressKeyPress = true;
				string seq = pklNoAcabadoTxt.Text.Trim();
				seq = seq.Replace(" ", string.Empty);
				if (seq == "" || seq == null || seq.Length > seqLength || seq.Length < seqLength)
				{
					MessageBox.Show("Introduce un número de Pedido (SEQ) válido!", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					pklNoAcabadoTxt.Clear();
				}
				else
				{
					ForzarPakingList(seq);
					pklNoAcabadoTxt.Clear();
					scanInput.Select();
				}
			}
		}

		private async void ForzarPakingList(string seq)
		{
			try
			{
				int totalQtyPe = 0;
				int currentReadQtyPe = 0;
				string pe = "";
				string box = "";
				HashSet<int> indexes = new HashSet<int>();
				for (int i = 0; i < articlesGrid.Rows.Count; i++)
				{
					if (articlesGrid.Rows[i].Cells["SEQ"].Value.ToString().Equals(seq) && !Convert.ToBoolean(articlesGrid.Rows[i].Cells["Finalizado"].Value.ToString()))
					{
						indexes.Add(i);
						pe = articlesGrid.Rows[i].Cells["PE"].Value.ToString();
						totalQtyPe += Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString());
						currentReadQtyPe += Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString());
						box = articlesGrid.Rows[i].Cells["Caja"].Value.ToString();
					}
				}
				if (!ECImode && currentReadQtyPe > 0 && (pe.Contains("/OUT/") || pe.Contains("/INT")) && !VPmode)
				{
					if (currentReadQtyPe == GetDoneQtySum(pe))
					{
						DataTable temporalClient = new DataTable();
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						_ = string.Empty;
						temporalClient = FetchClientInfoFromLivraison(company, pe);
						string cliente = temporalClient.Rows[0]["Name"].ToString();
						temporalClient.Rows[0]["Address"].ToString();
						temporalClient.Rows[0]["Complement"].ToString();
						temporalClient.Rows[0]["CodePostal"].ToString();
						temporalClient.Rows[0]["Ville"].ToString();
						temporalClient.Rows[0]["CodeRegion"].ToString();
						string pays = temporalClient.Rows[0]["Pays"].ToString();
						temporalClient.Rows[0]["Telephone"].ToString();
						temporalClient.Rows[0]["Email"].ToString();
						_ = string.Empty;
						if (DateTime.TryParse(temporalClient.Rows[0]["DeliveryDate"].ToString(), out var deliveryDateTime))
						{
							deliveryDateTime = Convert.ToDateTime(temporalClient.Rows[0]["DeliveryDate"].ToString());
							_ = $"{deliveryDateTime:dd/MM/yyyy}";
						}
						if (cliente == string.Empty && pe.Contains("/INT"))
						{
							cliente = FetchLocationName(company, pe);
						}
						if (cliente != string.Empty)
						{
							if (generateShipmentLabels && (db == companyIds["NATH"] || db == companyIds["ALAN"]))
							{
								lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
								panelScanPe.BackColor = default(Color);
								lblPe.Text = "ESPERE,\nVALIDANDO PEDIDO EN ODOO...";
								if (await Task.Run(() => GenerateCarrierLabelInOdoo(pe, temporalClient)))
								{
									lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
									lblPe.Text = "...VALIDADO \ud83d\udc4d";
									panelScanPe.BackColor = Color.LightGreen;
								}
								else
								{
									lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 48f);
									lblPe.Text = "...HUBO UN ERROR \ud83d\udc80";
									panelScanPe.BackColor = Color.Red;
								}
							}
							string matricula = string.Empty;
							if (MatriculaActiva)
							{
								// Modo matricula: cerrar la ultima caja en Odoo; si falla, el pedido no se termina
								if (!CerrarCajaEnOdoo(seq, pe, box, out matricula))
								{
									return;
								}
								indexes = IndicesPedido(pe);
							}
							string origin = string.Empty;
							if (company.Equals("EFFE"))
							{
								origin = temporalClient.Rows[0]["Origin"].ToString();
							}
							GenerateLabel(seq, pe, box, cliente, pays, last: true, origin, matricula);
							if (sendEmails)
							{
								sendEmailOnPeFinishedToConfigUser(pe, seq, currentReadQtyPe, cliente);
								sendEmailOnPeFinishedToGestor(pe, seq, currentReadQtyPe, cliente);
							}
							await Task.Run(delegate
							{
								if (crmLogs)
								{
									InsertOrderDoubleCheckingLogCrm(pe);
								}
							});
							sound_final.Play();
							FinishOrder(indexes, pe);
						}
						else
						{
							MessageBox.Show("Problema con el cliente", "Atencion", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
						}
					}
					else
					{
						MessageBox.Show("❌❌❌ Qty_done en Odoo es diferente de la que hay en el programa!!! ❌❌❌", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
				}
				else if (currentReadQtyPe > 0 && VPmode)
				{
					sound_final.Play();
					new DataTable();
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					_ = string.Empty;
					DataTable temporalClient2 = FetchClientInfoFromLivraison(company, pe);
					string cliente2 = temporalClient2.Rows[0]["Name"].ToString();
					temporalClient2.Rows[0]["Address"].ToString();
					temporalClient2.Rows[0]["Complement"].ToString();
					temporalClient2.Rows[0]["CodePostal"].ToString();
					temporalClient2.Rows[0]["Ville"].ToString();
					temporalClient2.Rows[0]["CodeRegion"].ToString();
					string pays2 = temporalClient2.Rows[0]["Pays"].ToString();
					temporalClient2.Rows[0]["Telephone"].ToString();
					temporalClient2.Rows[0]["Email"].ToString();
					_ = string.Empty;
					if (DateTime.TryParse(temporalClient2.Rows[0]["DeliveryDate"].ToString(), out var deliveryDateTime2))
					{
						deliveryDateTime2 = Convert.ToDateTime(temporalClient2.Rows[0]["DeliveryDate"].ToString());
						_ = $"{deliveryDateTime2:dd/MM/yyyy}";
					}
					if (cliente2 == string.Empty && pe.Contains("/INT"))
					{
						cliente2 = FetchLocationName(company, pe);
					}
					GenerateLabel(seq, pe, box, cliente2, pays2, last: true, string.Empty);
					if (sendEmails)
					{
						sendEmailOnPeFinishedToConfigUser(pe, seq, currentReadQtyPe, cliente2);
						sendEmailOnPeFinishedToGestor(pe, seq, currentReadQtyPe, cliente2);
					}
					if (crmLogs)
					{
						await Task.Run(delegate
						{
							InsertOrderDoubleCheckingLogCrm(pe);
						});
					}
					FinishOrder(indexes, pe);
				}
				else if (indexes.Count == 0)
				{
					MessageBox.Show("Este pedido ya esta finalizado // No se ha encontrado.", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
				else
				{
					MessageBox.Show("Este pedido no tiene articulos leidos.", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("ForzarPackingList_ " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private async void FinishOrder(HashSet<int> indexes, string order)
		{
			if (VPmode)
			{
				if (articlesGrid.Rows[indexes.FirstOrDefault()].Cells["LI_Intitule"].Value.ToString().Contains("#"))
				{
					Dictionary<string, int> parcelContentDict = new Dictionary<string, int>();
					List<string> stockOutData = new List<string>();
					string msg = "";
					string operation = articlesGrid.Rows[indexes.FirstOrDefault()].Cells["LI_Intitule"].Value.ToString().Split('#')[0];
					string batch = articlesGrid.Rows[indexes.FirstOrDefault()].Cells["LI_Intitule"].Value.ToString().Split('#')[1];
					string orderId = articlesGrid.Rows[indexes.FirstOrDefault()].Cells["LI_Intitule"].Value.ToString().Split('#')[2];
					foreach (int index in indexes)
					{
						if (Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value.ToString()) > 0)
						{
							if (!parcelContentDict.ContainsKey(articlesGrid.Rows[index].Cells["veepee_product_id"].Value.ToString()))
							{
								parcelContentDict.Add(articlesGrid.Rows[index].Cells["veepee_product_id"].Value.ToString(), Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value.ToString()));
							}
							else
							{
								parcelContentDict[articlesGrid.Rows[index].Cells["veepee_product_id"].Value.ToString()] = Convert.ToInt32(parcelContentDict[articlesGrid.Rows[index].Cells["veepee_product_id"].Value.ToString()]) + Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value.ToString());
							}
						}
						if (Convert.ToInt32(articlesGrid.Rows[index].Cells["QTY"].Value.ToString()) > Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value.ToString()))
						{
							int remainingQty = Convert.ToInt32(articlesGrid.Rows[index].Cells["QTY"].Value.ToString()) - Convert.ToInt32(articlesGrid.Rows[index].Cells["Leido"].Value.ToString());
							string stockOutString = string.Format("%s\r\n  \"deliveryOrderIds\": [\r\n {0},\r\n ],\r\n  \"productId\": {1},\r\n  \"quantity\": {2},\r\n %d", orderId, articlesGrid.Rows[index].Cells["veepee_product_id"].Value.ToString(), remainingQty.ToString());
							stockOutString = stockOutString.Replace("%s", "{").Replace("%d", "}");
							msg = msg + "\n" + stockOutString;
							stockOutData.Add(stockOutString);
						}
					}
					token = loginAndGetUserToken(userDict);
					if (token == null)
					{
						return;
					}
					string[] pdfName = generateParcelWithLabelOnFinishedDeliveryOrder(parcelContentDict, operation, batch, orderId);
					string readyShip = string.Empty;
					string shipped = string.Empty;
					if (stockOutData.Count > 0)
					{
						generateStockOutOnFinishedDeliveryOrder(stockOutData, operation, batch);
					}
					if (pdfName != null)
					{
						await Task.Run(delegate
						{
							PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", pdfName[0], 1);
							readyShip = "Fet";
							shipped = "Fet";
						});
						if (readyShip != null && shipped != null)
						{
							foreach (int index2 in indexes)
							{
								articlesGrid.Rows[index2].Cells["LI_Complement"].Value = pdfName[1];
								articlesGrid.Rows[index2].Cells["Finalizado"].Value = true;
								paintTable(index2);
							}
						}
					}
					logoutFromVP();
					parcelContentDict.Clear();
					stockOutData.Clear();
					logArticleLines();
				}
				else
				{
					sound_alert.Play();
					MessageBox.Show("Error formato Remarks del pedido", "Los remarks del pedido no tienen un formato correcto CAMPAIGN_NAME#BATCH_NUMBER#ORDER_ID", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
				return;
			}
			foreach (int index3 in indexes)
			{
				articlesGrid.Rows[index3].Cells["Finalizado"].Value = true;
				paintTable(index3);
			}
			logArticleLines();
		}

		private void UpdateDoneQtyByOrderNumber(string order, int qty_leido, string product_code, string ean_code, int sml_id)
		{
			if (modoPrueba)
			{
				LogPrueba("UPDATE stock_move_line no hecho: id=" + sml_id + " " + order + " EAN " + ean_code + " qty_done=" + qty_leido);
				return;
			}
			try
			{
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryUpdateStockMoveLine, cSql.dbConn);
					npgsqlCommand.Parameters.AddWithValue("@qty", qty_leido);
					npgsqlCommand.Parameters.AddWithValue("@id", sml_id);
					npgsqlCommand.Parameters.AddWithValue("@order", order);
					npgsqlCommand.Parameters.AddWithValue("@default_code", product_code);
					npgsqlCommand.Parameters.AddWithValue("@ean_code", ean_code);
					if (company.Equals("TTUC"))
					{
						if (order.StartsWith("W_CAD"))
						{
							db = companyIds["TTUC_CAD"];
						}
						else if (order.StartsWith("W_COP"))
						{
							db = companyIds["TTUC_COP"];
						}
						else if (order.StartsWith("W_USA"))
						{
							db = companyIds["TTUC_USA"];
						}
					}
					if (company.Equals("ALAN") && order.StartsWith("CAREY"))
					{
						db = companyIds["CAREY"];
					}
					npgsqlCommand.Parameters.AddWithValue("@company_id", db);
					npgsqlCommand.ExecuteNonQuery();
					cSql.dbConn.Close();
				}
			}
			catch (Exception ex)
			{
				sound_alert.Play();
				MessageBox.Show(ex.TargetSite.Name + " " + ex.Message, "Error de conexión a ODOO", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				UpdateDoneQtyByOrderNumber(order, qty_leido, product_code, ean_code, sml_id);
			}
		}

		private int GetDoneQtySum(string order)
		{
			if (modoPrueba)
			{
				return SumaLeidoEnMemoria(order);
			}
			try
			{
				int value = 0;
				using (ConnectionSQL cSql = new ConnectionSQL(company))
				{
					cSql.dbConn.Open();
					NpgsqlCommand npgsqlCommand = new NpgsqlCommand(queryGetSumStockMoveLines, cSql.dbConn);
					npgsqlCommand.Parameters.AddWithValue("@order", order);
					if (company.Equals("TTUC"))
					{
						if (order.StartsWith("W_CAD"))
						{
							db = companyIds["TTUC_CAD"];
						}
						else if (order.StartsWith("W_COP"))
						{
							db = companyIds["TTUC_COP"];
						}
						else if (order.StartsWith("W_USA"))
						{
							db = companyIds["TTUC_USA"];
						}
					}
					if (company.Equals("ALAN") && order.StartsWith("CAREY"))
					{
						db = companyIds["CAREY"];
					}
					npgsqlCommand.Parameters.AddWithValue("@company_id", db);
					NpgsqlDataReader reader = npgsqlCommand.ExecuteReader();
					if (reader.HasRows)
					{
						reader.Read();
						value = Convert.ToInt32(reader["qty_done"].ToString());
						reader.Close();
					}
					cSql.dbConn.Close();
				}
				return value;
			}
			catch (Exception ex)
			{
				MessageBox.Show("GetDoneQtySum_ " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return 0;
			}
		}

		private void Speak(string phrase)
		{
			synth.Rate = 3;
			synth.SelectVoice(ReturnSetting("voice"));
			synth.SpeakAsync(phrase);
		}

		private void pklTemporalTxt_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
			}
			else if (e.KeyCode == Keys.Return)
			{
				e.SuppressKeyPress = true;
				string seq = pklTemporalTxt.Text.Trim();
				seq = seq.Replace(" ", string.Empty);
				if (seq == "" || seq == null || seq.Length > seqLength || seq.Length < seqLength)
				{
					MessageBox.Show("Introduce un número de Pedido (SEQ) válido!", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					pklTemporalTxt.Clear();
				}
				else
				{
					PrintPackingListAndPendientes(seq);
					pklTemporalTxt.Clear();
					scanInput.Select();
				}
			}
		}

		private async void PrintPackingListAndPendientes(string seq)
		{
			try
			{
				int totalQtyPe = 0;
				int currentReadQtyPe = 0;
				string pe = "";
				string box = "";
				for (int i = 0; i < articlesGrid.Rows.Count; i++)
				{
					if (articlesGrid.Rows[i].Cells["SEQ"].Value.ToString().Equals(seq))
					{
						pe = articlesGrid.Rows[i].Cells["PE"].Value.ToString();
						totalQtyPe += Convert.ToInt32(articlesGrid.Rows[i].Cells["QTY"].Value.ToString());
						currentReadQtyPe += Convert.ToInt32(articlesGrid.Rows[i].Cells["Leido"].Value.ToString());
						box = articlesGrid.Rows[i].Cells["Caja"].Value.ToString();
					}
				}
				if (!ECImode && currentReadQtyPe > 0 && (pe.Contains("/OUT/") || pe.Contains("/INT")))
				{
					new DataTable();
					string cliente = string.Empty;
					string address = string.Empty;
					string complement = string.Empty;
					string codePostal = string.Empty;
					string ville = string.Empty;
					string codeRegion = string.Empty;
					string pays = string.Empty;
					string telephone = string.Empty;
					string email = string.Empty;
					string deliveryDate = string.Empty;
					DataTable temporalClient = FetchClientInfoFromLivraison(company, pe);
					cliente = temporalClient.Rows[0]["Name"].ToString();
					address = temporalClient.Rows[0]["Address"].ToString();
					complement = temporalClient.Rows[0]["Complement"].ToString();
					codePostal = temporalClient.Rows[0]["CodePostal"].ToString();
					ville = temporalClient.Rows[0]["Ville"].ToString();
					codeRegion = temporalClient.Rows[0]["CodeRegion"].ToString();
					pays = temporalClient.Rows[0]["Pays"].ToString();
					telephone = temporalClient.Rows[0]["Telephone"].ToString();
					email = temporalClient.Rows[0]["Email"].ToString();
					deliveryDate = string.Empty;
					if (DateTime.TryParse(temporalClient.Rows[0]["DeliveryDate"].ToString(), out var deliveryDateTime))
					{
						deliveryDateTime = Convert.ToDateTime(temporalClient.Rows[0]["DeliveryDate"].ToString());
						deliveryDate = $"{deliveryDateTime:dd/MM/yyyy}";
					}
					if (cliente == string.Empty && pe.Contains("/INT"))
					{
						cliente = FetchLocationName(company, pe);
					}
					if (!(cliente != string.Empty))
					{
						return;
					}
					await Task.Run(delegate
					{
						GeneratePackingListPDF(pe, cliente, address, complement, codePostal, ville, codeRegion, pays, telephone, email, currentReadQtyPe, box, deliveryDate);
						if (AnyPendingArticles())
						{
							Thread.Sleep(10000);
							ExportPendingArticlesToPDF(articlesGrid, print: true, question: false);
						}
					});
				}
				else
				{
					MessageBox.Show("Este pedido no tiene articulos leidos.", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("PrintPackingListAndPendientes " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void boxLblPrintTxt_KeyDown(object sender, KeyEventArgs e)
		{
			try
			{
				if (e.KeyCode == Keys.Escape)
				{
					e.SuppressKeyPress = true;
				}
				else
				{
					if (e.KeyCode != Keys.Return)
					{
						return;
					}
					e.SuppressKeyPress = true;
					string seq = boxLblPrintTxt.Text.Trim();
					seq = seq.Replace(" ", string.Empty);
					if (seq == "" || seq == null || seq.Length != seqLength)
					{
						MessageBox.Show("Introduce un número de Pedido (SEQ) válido!", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
					else if (VPmode && !ECImode)
					{
						string operation = string.Empty;
						string batch = string.Empty;
						string order = string.Empty;
						string parcelId = string.Empty;
						HashSet<int> indexes = new HashSet<int>();
						foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
						{
							if (row.Cells["SEQ"].Value.ToString().Equals(seq))
							{
								indexes.Add(row.Index);
								operation = row.Cells["LI_Intitule"].Value.ToString().Split('#')[0];
								batch = row.Cells["LI_Intitule"].Value.ToString().Split('#')[1];
								order = row.Cells["LI_Intitule"].Value.ToString().Split('#')[2];
								parcelId = row.Cells["LI_Complement"].Value.ToString();
							}
						}
						string fileName = string.Empty;
						token = loginAndGetUserToken(userDict);
						if (token != null)
						{
							fileName = GetLabelOfExistingParcel(operation, batch, parcelId);
							if (fileName != null)
							{
								PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", fileName, 1);
							}
							logoutFromVP();
						}
						if (fileName == null && MessageBox.Show("Falta el Parcel ID, generar parcel de nuevo?", "Parcel ID no disponible", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
						{
							FinishOrder(indexes, order);
						}
					}
					else if (generateShipmentLabels && !VPmode && !ECImode)
					{
						string etiquetasPath = Path.Combine(appPath, "Labels");
						string order2 = string.Empty;
						foreach (DataGridViewRow row2 in (IEnumerable)articlesGrid.Rows)
						{
							if (row2.Cells["SEQ"].Value.ToString().Equals(seq))
							{
								order2 = row2.Cells["PE"].Value.ToString().Replace("/", "_");
								break;
							}
						}
						IEnumerable<string> files = from f in Directory.GetFiles(etiquetasPath)
							where f.Contains(order2)
							select f;
						if (files.Count() > 0)
						{
							foreach (string file in files)
							{
								PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", file, 1);
							}
						}
						else
						{
							MessageBox.Show("No hay etiquetas para este pedido ", "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
						}
					}
					else
					{
						MessageBox.Show("Solo reimprime si: \n- (Modo VP y NO Modo ECI) \n- (Generar Etiquetas Envio y NO Modo VP y NO Modo ECI)", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
					boxLblPrintTxt.Clear();
					scanInput.Select();
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show("boxLblPrintTxt_KeyDown " + ex, "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void buscarActualizacionesToolStripMenuItem_Click(object sender, EventArgs e)
		{
			AutoUpdater.HttpUserAgent = "AutoUpdater";
			AutoUpdater.ReportErrors = true;
			AutoUpdater.RunUpdateAsAdmin = false;
			if (!new WebClient().DownloadString("http://ipinfo.io/ip").Equals(ReturnSetting("public_ip")))
			{
				AutoUpdater.Start("https://nathserver.synology.me/updates/pedidos_multiples_odoo.xml", new NetworkCredential("update_user", "@Actualizacion010"));
			}
			else
			{
				AutoUpdater.Start("http://192.168.0.50/updates/pedidos_multiples_odoo.xml", new NetworkCredential("update_user", "@Actualizacion010"));
			}
		}

		private void generarEtiquetasEnvioToolStripMenuItem_Click(object sender, EventArgs e)
		{
			try
			{
				if (company == null || company == "")
				{
					MessageBox.Show("Selecciona una base de datos", "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
				else if (MessageBox.Show("Cambiar de modo?", "Cambiar modo ETIQUETAS", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
				{
					cambiarModo(sender);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex.Message);
			}
		}

		private bool GenerateCarrierLabelInOdoo(string order, DataTable orderInfo)
		{
			if (modoPrueba)
			{
				LogPrueba("Validacion en Odoo y etiqueta de transportista no hechas: " + order);
				return false;
			}
			try
			{
				int packageTypeId = 0;
				int carrierId = 0;
				HashSet<string> IberianCountryCodes = new HashSet<string> { "ES", "PT" };
				HashSet<string> obj = new HashSet<string> { "35500", "CE", "GC", "ME", "TF" };
				string origin = orderInfo.Rows[0]["Origin"].ToString().ToLower();
				string countryCode = orderInfo.Rows[0]["CountryCode"].ToString();
				string provinceCode = orderInfo.Rows[0]["ProvinceCode"].ToString();
				bool isIberianCountry = IberianCountryCodes.Contains(countryCode);
				if (obj.Contains(provinceCode))
				{
					throw new FileNotFoundException("Province is Ceuta, Las Palmas, Melilla or Tenerife.");
				}
				if (origin.StartsWith("eci-") && db == companyIds["NATH"])
				{
					packageTypeId = 28;
					carrierId = 327;
				}
				else if (origin.StartsWith("eci-") && db == companyIds["ALAN"])
				{
					packageTypeId = 28;
					carrierId = 329;
				}
				else if (origin.StartsWith("w") && db == companyIds["NATH"])
				{
					packageTypeId = 27;
					carrierId = ((!isIberianCountry) ? 298 : 89);
				}
				else if (origin.StartsWith("w") && db == companyIds["ALAN"])
				{
					packageTypeId = 8579;
					if (isIberianCountry)
					{
						carrierId = 261;
					}
				}
				else if (origin.StartsWith("vp-") && db == companyIds["NATH"])
				{
					packageTypeId = 28;
					carrierId = ((!isIberianCountry) ? 298 : 324);
				}
				else if (origin.StartsWith("vp-") && db == companyIds["ALAN"])
				{
					packageTypeId = 28;
					if (isIberianCountry)
					{
						carrierId = 261;
					}
				}
				else if (origin.StartsWith("srp-") && db == companyIds["NATH"])
				{
					packageTypeId = 28;
					carrierId = ((!isIberianCountry) ? 298 : 89);
				}
				else if (origin.StartsWith("vbd-") && db == companyIds["NATH"])
				{
					packageTypeId = 28;
					carrierId = ((!isIberianCountry) ? 298 : 89);
				}
				else if (origin.StartsWith("ds-") && db == companyIds["NATH"])
				{
					packageTypeId = 28;
					carrierId = ((!isIberianCountry) ? 298 : 89);
				}
				string odooLabel = envios.ValidateOrder(order, db, carrierId, packageTypeId);
				if (odooLabel.Equals(string.Empty) || !File.Exists(odooLabel))
				{
					throw new FileNotFoundException("odooLabel is empty and label file does not exist.");
				}
				string eciOrderNumber = string.Empty;
				if (orderInfo.Rows[0]["EciDelivery"].ToString().Equals("Entrega en centro comercial") && origin.Contains("eci-") && orderInfo.Rows[0]["Remarks"].ToString().Length > 0)
				{
					eciOrderNumber = ((!orderInfo.Rows[0]["Remarks"].ToString().Contains("-A")) ? (orderInfo.Rows[0]["Remarks"].ToString() + "-A") : orderInfo.Rows[0]["Remarks"].ToString());
				}
				if (eciOrderNumber.Length > 0)
				{
					string eciDocId = envios.GetEciDocuments(eciOrderNumber);
					if (eciDocId == null)
					{
						throw new FileNotFoundException("eciDocId is null");
					}
					string eciLabelFile = envios.GetEciLabel(order, eciDocId, labelPath);
					if (eciLabelFile != null)
					{
						PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", eciLabelFile, 1);
					}
				}
				PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", odooLabel, 1);
				return true;
			}
			catch (FileNotFoundException ex)
			{
				if (ex.Message.Equals("eciDocId is null"))
				{
					if (File.Exists(eciPdfLabel))
					{
						PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", eciPdfLabel, 1);
					}
				}
				else if (File.Exists(defaultPdfLabel))
				{
					PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", defaultPdfLabel, 1);
				}
				return false;
			}
			catch (Exception ex2)
			{
				ExceptionLogging.LogExceptionToFile(ex2);
				return false;
			}
		}

		private string[] generateParcelWithLabelOnFinishedDeliveryOrder(Dictionary<string, int> dict, string operation, string batch, string order)
		{
			HttpWebResponse response = null;
			try
			{
				string request_params = JsonConvert.SerializeObject(dict);
				byte[] bytes = Encoding.UTF8.GetBytes(request_params);
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/parcels/operation/{1}/batch/{2}/deliveryorder/{3}/label?labelType=Pdf&labelDpi=203", api_version, operation, batch, order));
				obj.Method = "POST";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = bytes.Length;
				Stream requestStream = obj.GetRequestStream();
				requestStream.Write(bytes, 0, bytes.Length);
				requestStream.Close();
				response = (HttpWebResponse)obj.GetResponse();
				dynamic stuff = JsonConvert.DeserializeObject(new StreamReader(response.GetResponseStream()).ReadToEnd());
				string parcelId = stuff["id"];
				string fileContents = stuff["fileContents"];
				string fileName = stuff["fileName"];
				string etiquetasPath = Path.Combine(appPath, "Etiquetas VP", operation, batch);
				if (!Directory.Exists(etiquetasPath))
				{
					Directory.CreateDirectory(etiquetasPath);
				}
				string pdfFilename = Path.Combine(etiquetasPath, fileName);
				byte[] buffer = Convert.FromBase64String(fileContents);
				using (Stream writer = File.Create(pdfFilename))
				{
					writer.Write(buffer, 0, buffer.Length);
					writer.Flush();
				}
				return new string[2] { pdfFilename, parcelId };
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return generateParcelWithLabelOnFinishedDeliveryOrder(dict, operation, batch, order);
					}
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private List<string> generateStockOutOnFinishedDeliveryOrder(List<string> list, string operation, string batch)
		{
			HttpWebResponse response = null;
			try
			{
				List<string> results = new List<string>();
				foreach (string line in list)
				{
					byte[] bytes = Encoding.UTF8.GetBytes(line);
					HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/stocks/{1}/batch/{2}/stockout", api_version, operation, batch));
					obj.Method = "POST";
					obj.ContentType = "application/json";
					obj.Headers.Add("Authorization", "Bearer " + token);
					obj.ContentLength = bytes.Length;
					Stream requestStream = obj.GetRequestStream();
					requestStream.Write(bytes, 0, bytes.Length);
					requestStream.Close();
					response = (HttpWebResponse)obj.GetResponse();
					dynamic stuff = JsonConvert.DeserializeObject(new StreamReader(response.GetResponseStream()).ReadToEnd());
					results.Add(stuff);
				}
				return results;
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return generateStockOutOnFinishedDeliveryOrder(list, operation, batch);
					}
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private string loginAndGetUserToken(object obj)
		{
			HttpWebResponse response = null;
			string response_reader = string.Empty;
			string result = string.Empty;
			try
			{
				string request_params = JsonConvert.SerializeObject(obj);
				byte[] bytes = Encoding.UTF8.GetBytes(request_params);
				HttpWebRequest obj2 = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/auth/login", api_version));
				obj2.Method = "POST";
				obj2.ContentType = "application/json";
				obj2.ContentLength = bytes.Length;
				Stream requestStream = obj2.GetRequestStream();
				requestStream.Write(bytes, 0, bytes.Length);
				requestStream.Close();
				response = (HttpWebResponse)obj2.GetResponse();
				response_reader = new StreamReader(response.GetResponseStream()).ReadToEnd();
				if (response_reader.Length > 0)
				{
					result = JObject.Parse(response_reader).Value<string>("access_token");
				}
				return result;
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return loginAndGetUserToken(obj);
					}
				}
				return null;
			}
			finally
			{
				if (response != null && response_reader.Length > 0)
				{
					response.Close();
				}
			}
		}

		private void logoutFromVP()
		{
			HttpWebResponse response = null;
			try
			{
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/auth/logout", api_version));
				obj.Method = "POST";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = 0L;
				response = (HttpWebResponse)obj.GetResponse();
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						logoutFromVP();
					}
				}
			}
			finally
			{
				response?.Close();
			}
		}

		private string shipParcelsWhenOrderFinished(string parcelId)
		{
			HttpWebResponse response = null;
			try
			{
				string operation = articlesGrid.Rows[0].Cells["LI_Intitule"].Value.ToString().Split('#')[0];
				string batch = articlesGrid.Rows[0].Cells["LI_Intitule"].Value.ToString().Split('#')[1];
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/parcels/operation/{1}/batch/{2}/parcel/{3}/ship", api_version, operation, batch, parcelId));
				obj.Method = "POST";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = 0L;
				response = (HttpWebResponse)obj.GetResponse();
				dynamic stuff = JsonConvert.DeserializeObject(new StreamReader(response.GetResponseStream()).ReadToEnd());
				return stuff.ToString();
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return shipParcelsWhenOrderFinished(parcelId);
					}
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private string readyToShipParcelWhenOrderFinished(string parcelId)
		{
			HttpWebResponse response = null;
			try
			{
				string operation = articlesGrid.Rows[0].Cells["LI_Intitule"].Value.ToString().Split('#')[0];
				string batch = articlesGrid.Rows[0].Cells["LI_Intitule"].Value.ToString().Split('#')[1];
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/parcels/operation/{1}/batch/{2}/parcel/{3}/readytoship", api_version, operation, batch, parcelId));
				obj.Method = "POST";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = 0L;
				response = (HttpWebResponse)obj.GetResponse();
				dynamic stuff = JsonConvert.DeserializeObject(new StreamReader(response.GetResponseStream()).ReadToEnd());
				return stuff.ToString();
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return readyToShipParcelWhenOrderFinished(parcelId);
					}
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private void rePrintVpLabelBox_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
			}
			else
			{
				if (e.KeyCode != Keys.Return)
				{
					return;
				}
				e.SuppressKeyPress = true;
				if (articlesGrid.Rows.Count > 0)
				{
					string veepeeRef = rePrintVpLabelBox.Text.Trim();
					string operation = string.Empty;
					string batch = string.Empty;
					_ = string.Empty;
					string parcelId = string.Empty;
					foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
					{
						if (row.Cells["veepee_ref"].Value.ToString().Equals(veepeeRef))
						{
							operation = row.Cells["LI_Intitule"].Value.ToString().Split('#')[0];
							batch = row.Cells["LI_Intitule"].Value.ToString().Split('#')[1];
							row.Cells["PE"].Value.ToString();
							parcelId = row.Cells["LI_Complement"].Value.ToString();
							break;
						}
					}
					IEnumerable<string> files = from f in Directory.GetFiles(Path.Combine(appPath, "Etiquetas VP", operation, batch))
						where f.Contains(parcelId)
						select f;
					if (files.Count() > 0)
					{
						string fileName = files.LastOrDefault();
						if (fileName != null)
						{
							PrintPDF(ReturnSetting("imp_tick_small").ToString(), "A6", fileName, 1);
						}
					}
					else
					{
						MessageBox.Show("No se ha encontrado etiqueta para esa referencia.", "Atención", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					}
					rePrintVpLabelBox.Clear();
					scanInput.Select();
				}
				else
				{
					MessageBox.Show("No hay líneas cargadas.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				}
			}
		}

		private string GetLabelOfExistingParcel(string operation, string batch, string parcelId)
		{
			HttpWebResponse response = null;
			try
			{
				string etiquetasPath = Path.Combine(appPath, "Etiquetas VP", operation, batch);
				if (!Directory.Exists(etiquetasPath))
				{
					Directory.CreateDirectory(etiquetasPath);
				}
				if (parcelId.Length == 0)
				{
					return null;
				}
				IEnumerable<string> files = from f in Directory.GetFiles(etiquetasPath)
					where f.Contains(parcelId)
					select f;
				if (files.Count() > 0)
				{
					return files.LastOrDefault();
				}
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/parcels/operation/{1}/batch/{2}/parcel/{3}/label?labelType=Pdf&labelDpi=203", api_version, operation, batch, parcelId));
				obj.Method = "PUT";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = 0L;
				response = (HttpWebResponse)obj.GetResponse();
				string fileName = $"label_{operation}_{batch}_{parcelId}_manual.pdf";
				string pdfFilename = Path.Combine(etiquetasPath, fileName);
				using (FileStream stream = File.Create(pdfFilename))
				{
					response.GetResponseStream().CopyTo(stream);
				}
				return pdfFilename;
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private string getOpenWarehousePalletIdByCode(string palletCode)
		{
			HttpWebResponse response = null;
			try
			{
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/pallet/list/warehouse/{1}", api_version, warehouse_id));
				obj.Method = "GET";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = 0L;
				response = (HttpWebResponse)obj.GetResponse();
				dynamic stuff = JsonConvert.DeserializeObject(new StreamReader(response.GetResponseStream()).ReadToEnd());
				string result = string.Empty;
				foreach (dynamic element in stuff)
				{
					if (element["status"].ToString().Equals("Open") && element["code"].ToString().Equals(palletCode))
					{
						result = element["id"].ToString();
						break;
					}
				}
				return result;
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return getOpenWarehousePalletIdByCode(palletCode);
					}
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private string assignFinishedOrdersParcelsToPallet(int[] parcelIdsArray, string palletId)
		{
			HttpWebResponse response = null;
			try
			{
				string parcelIdsString = "[" + string.Join(", ", parcelIdsArray) + "]";
				byte[] bytes = Encoding.UTF8.GetBytes(parcelIdsString);
				HttpWebRequest obj = (HttpWebRequest)WebRequest.Create(string.Format(base_url + "/api/v{0}/pallet/{1}/parcel/add", api_version, palletId));
				obj.Method = "PATCH";
				obj.ContentType = "application/json";
				obj.Headers.Add("Authorization", "Bearer " + token);
				obj.ContentLength = bytes.Length;
				Stream requestStream = obj.GetRequestStream();
				requestStream.Write(bytes, 0, bytes.Length);
				requestStream.Close();
				response = (HttpWebResponse)obj.GetResponse();
				string text = new StreamReader(response.GetResponseStream()).ReadToEnd();
				JsonConvert.DeserializeObject(text);
				return text;
			}
			catch (WebException ex)
			{
				if (ex.Status == WebExceptionStatus.ProtocolError)
				{
					response = (HttpWebResponse)ex.Response;
					StreamReader streamReader = new StreamReader(response.GetResponseStream());
					MessageBox.Show(string.Format(arg1: streamReader.ReadToEnd(), format: "Errorcode: {0}, Message: {1}", arg0: (int)response.StatusCode), "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					streamReader.Close();
				}
				else
				{
					MessageBox.Show($"Error: {ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
					if (MessageBox.Show("Hubo un error, volver a probar?", "Volver a probar", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
					{
						return assignFinishedOrdersParcelsToPallet(parcelIdsArray, palletId);
					}
				}
				return null;
			}
			finally
			{
				response?.Close();
			}
		}

		private void assignPaletBtn_Click(object sender, EventArgs e)
		{
			if (!VPmode || MessageBox.Show("Asignar a ese pallet?", "Pallet", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
			{
				return;
			}
			token = loginAndGetUserToken(userDict);
			if (token != null)
			{
				string palletCode = palletNumBox.Text.ToString().Trim();
				if (palletCode.Length > 0)
				{
					string palletId = getOpenWarehousePalletIdByCode(palletCode);
					if (palletId.Length > 0)
					{
						HashSet<int> parcelSet = new HashSet<int>();
						HashSet<int> indexes = new HashSet<int>();
						foreach (DataGridViewRow row in (IEnumerable)articlesGrid.Rows)
						{
							if (Convert.ToBoolean(row.Cells["Finalizado"].Value.ToString()) && !row.Cells["LI_Complement"].Value.ToString().Equals("parcel_id") && row.Cells["LI_Pallet"].Value.ToString().Equals("pallet_id"))
							{
								indexes.Add(row.Index);
								parcelSet.Add(Convert.ToInt32(row.Cells["LI_Complement"].Value.ToString()));
							}
						}
						if (parcelSet.Count > 0 && assignFinishedOrdersParcelsToPallet(parcelSet.ToArray(), palletId) != null)
						{
							foreach (int index in indexes)
							{
								articlesGrid.Rows[index].Cells["LI_Pallet"].Value = palletId;
							}
							logArticleLines();
						}
					}
					else
					{
						MessageBox.Show("No se ha encontrado este pallet, revisar por si esta Cancelado / Cerrado.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
					}
				}
				logoutFromVP();
			}
			palletNumBox.Clear();
		}

		protected override void Dispose(bool disposing)
		{
			if (disposing && components != null)
			{
				components.Dispose();
			}
			base.Dispose(disposing);
		}

		private void InitializeComponent()
		{
			this.components = new System.ComponentModel.Container();
			System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(PedidosMultiples.InitialForm));
			this.menuStrip1 = new System.Windows.Forms.MenuStrip();
			this.baseDeDatosToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.nATH1ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.aLANToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.codeToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.tCNToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.tUCTUCToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.eFFECTIVEToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.históricoToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.NathRecuperar = new System.Windows.Forms.ToolStripMenuItem();
			this.AlanRecuperar = new System.Windows.Forms.ToolStripMenuItem();
			this.CodeRecuperar = new System.Windows.Forms.ToolStripMenuItem();
			this.TcnRecuperar = new System.Windows.Forms.ToolStripMenuItem();
			this.TtucRecuperar = new System.Windows.Forms.ToolStripMenuItem();
			this.EffectiveRecuperar = new System.Windows.Forms.ToolStripMenuItem();
			this.opcionesToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.enviarEmailsToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.imprimirPackingToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.imprimirEtiquetasCajaToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.generarEtiquetasEnvioToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.modoECIToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.modoVPToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.configuraciónToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.buscarActualizacionesToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
			this.statusStrip1 = new System.Windows.Forms.StatusStrip();
			this.VersionLabel = new System.Windows.Forms.ToolStripStatusLabel();
			this.toolStripStatusLabel1 = new System.Windows.Forms.ToolStripStatusLabel();
			this.serverIpLbl = new System.Windows.Forms.ToolStripStatusLabel();
			this.toolStripStatusLabel2 = new System.Windows.Forms.ToolStripStatusLabel();
			this.databaseNameLbl = new System.Windows.Forms.ToolStripStatusLabel();
			this.modeStatusLabel = new System.Windows.Forms.ToolStripStatusLabel();
			this.panelScanPe = new System.Windows.Forms.Panel();
			this.modoVPGroupBox = new System.Windows.Forms.GroupBox();
			this.palletNumBox = new System.Windows.Forms.TextBox();
			this.rePrintVpLabelBox = new System.Windows.Forms.TextBox();
			this.label4 = new System.Windows.Forms.Label();
			this.assignPaletBtn = new System.Windows.Forms.Button();
			this.label3 = new System.Windows.Forms.Label();
			this.boxLblPrintTxt = new System.Windows.Forms.TextBox();
			this._shiftPausedTimeDisplay = new System.Windows.Forms.Label();
			this._shiftTotalTimeDisplay = new System.Windows.Forms.Label();
			this.shiftProductivityLabel = new System.Windows.Forms.Label();
			this.shiftScansLabel = new System.Windows.Forms.Label();
			this.pklTemporalTxt = new System.Windows.Forms.TextBox();
			this.label2 = new System.Windows.Forms.Label();
			this.pklNoAcabadoTxt = new System.Windows.Forms.TextBox();
			this.label1 = new System.Windows.Forms.Label();
			this.pendientesPedidoBox = new System.Windows.Forms.TextBox();
			this.pendientesPedidoLabel = new System.Windows.Forms.Label();
			this.nombreOleadaLbl = new System.Windows.Forms.Label();
			this.nombreOleadaTxt = new System.Windows.Forms.TextBox();
			this.timeRemainingLbl = new System.Windows.Forms.Label();
			this.filtroPendBtn = new System.Windows.Forms.Button();
			this.totalUnitsHourLbl = new System.Windows.Forms.Label();
			this.productivityBtn = new System.Windows.Forms.Button();
			this.pauseTimerBtn = new System.Windows.Forms.Button();
			this._totalElapsedTimeDisplay = new System.Windows.Forms.Label();
			this.pendingArticlesBtn = new System.Windows.Forms.Button();
			this.seqValueLbl = new System.Windows.Forms.Label();
			this.nextBoxBtn = new System.Windows.Forms.Button();
			this.newBoxTxt = new System.Windows.Forms.TextBox();
			this.nextBtn = new System.Windows.Forms.Button();
			this.scanInput = new System.Windows.Forms.TextBox();
			this.lblPe = new System.Windows.Forms.Label();
			this.panelTable = new System.Windows.Forms.Panel();
			this.articlesGrid = new System.Windows.Forms.DataGridView();
			this.progressBarTotal = new System.Windows.Forms.Panel();
			this.toolTip1 = new System.Windows.Forms.ToolTip(this.components);
			this.menuStrip1.SuspendLayout();
			this.statusStrip1.SuspendLayout();
			this.panelScanPe.SuspendLayout();
			this.modoVPGroupBox.SuspendLayout();
			this.panelTable.SuspendLayout();
			((System.ComponentModel.ISupportInitialize)this.articlesGrid).BeginInit();
			base.SuspendLayout();
			this.menuStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[3] { this.baseDeDatosToolStripMenuItem, this.históricoToolStripMenuItem, this.opcionesToolStripMenuItem });
			this.menuStrip1.Location = new System.Drawing.Point(0, 0);
			this.menuStrip1.Name = "menuStrip1";
			this.menuStrip1.Size = new System.Drawing.Size(1008, 24);
			this.menuStrip1.TabIndex = 0;
			this.menuStrip1.Text = "menuStrip1";
			this.baseDeDatosToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[6] { this.nATH1ToolStripMenuItem, this.aLANToolStripMenuItem, this.codeToolStripMenuItem, this.tCNToolStripMenuItem, this.tUCTUCToolStripMenuItem, this.eFFECTIVEToolStripMenuItem });
			this.baseDeDatosToolStripMenuItem.Name = "baseDeDatosToolStripMenuItem";
			this.baseDeDatosToolStripMenuItem.Size = new System.Drawing.Size(64, 20);
			this.baseDeDatosToolStripMenuItem.Text = "Empresa";
			this.nATH1ToolStripMenuItem.Enabled = false;
			this.nATH1ToolStripMenuItem.Name = "nATH1ToolStripMenuItem";
			this.nATH1ToolStripMenuItem.Size = new System.Drawing.Size(128, 22);
			this.nATH1ToolStripMenuItem.Text = "NATH";
			this.nATH1ToolStripMenuItem.Visible = false;
			this.nATH1ToolStripMenuItem.Click += new System.EventHandler(nATH1ToolStripMenuItem_Click);
			this.aLANToolStripMenuItem.Name = "aLANToolStripMenuItem";
			this.aLANToolStripMenuItem.Size = new System.Drawing.Size(128, 22);
			this.aLANToolStripMenuItem.Text = "ALAN";
			this.aLANToolStripMenuItem.Click += new System.EventHandler(aLANToolStripMenuItem_Click);
			this.codeToolStripMenuItem.Name = "codeToolStripMenuItem";
			this.codeToolStripMenuItem.Size = new System.Drawing.Size(128, 22);
			this.codeToolStripMenuItem.Text = "CODE";
			this.codeToolStripMenuItem.Click += new System.EventHandler(codeToolStripMenuItem_Click);
			this.tCNToolStripMenuItem.Name = "tCNToolStripMenuItem";
			this.tCNToolStripMenuItem.Size = new System.Drawing.Size(128, 22);
			this.tCNToolStripMenuItem.Text = "TCN";
			this.tCNToolStripMenuItem.Click += new System.EventHandler(tCNToolStripMenuItem_Click);
			this.tUCTUCToolStripMenuItem.Name = "tUCTUCToolStripMenuItem";
			this.tUCTUCToolStripMenuItem.Size = new System.Drawing.Size(128, 22);
			this.tUCTUCToolStripMenuItem.Text = "TUC TUC";
			this.tUCTUCToolStripMenuItem.Click += new System.EventHandler(tUCTUCToolStripMenuItem_Click);
			this.eFFECTIVEToolStripMenuItem.Name = "eFFECTIVEToolStripMenuItem";
			this.eFFECTIVEToolStripMenuItem.Size = new System.Drawing.Size(128, 22);
			this.eFFECTIVEToolStripMenuItem.Text = "EFFECTIVE";
			this.eFFECTIVEToolStripMenuItem.Click += new System.EventHandler(eFFECTIVEToolStripMenuItem_Click);
			this.históricoToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[6] { this.NathRecuperar, this.AlanRecuperar, this.CodeRecuperar, this.TcnRecuperar, this.TtucRecuperar, this.EffectiveRecuperar });
			this.históricoToolStripMenuItem.Name = "históricoToolStripMenuItem";
			this.históricoToolStripMenuItem.Size = new System.Drawing.Size(95, 20);
			this.históricoToolStripMenuItem.Text = "Ultimo pedido";
			this.NathRecuperar.Name = "NathRecuperar";
			this.NathRecuperar.Size = new System.Drawing.Size(180, 22);
			this.NathRecuperar.Text = "NATH";
			this.NathRecuperar.Click += new System.EventHandler(NathRecuperar_Click);
			this.AlanRecuperar.Name = "AlanRecuperar";
			this.AlanRecuperar.Size = new System.Drawing.Size(180, 22);
			this.AlanRecuperar.Text = "ALAN";
			this.AlanRecuperar.Click += new System.EventHandler(AlanRecuperar_Click);
			this.CodeRecuperar.Name = "CodeRecuperar";
			this.CodeRecuperar.Size = new System.Drawing.Size(180, 22);
			this.CodeRecuperar.Text = "CODE";
			this.CodeRecuperar.Click += new System.EventHandler(CodeRecuperar_Click);
			this.TcnRecuperar.Name = "TcnRecuperar";
			this.TcnRecuperar.Size = new System.Drawing.Size(180, 22);
			this.TcnRecuperar.Text = "TCN";
			this.TcnRecuperar.Click += new System.EventHandler(TcnRecuperar_Click);
			this.TtucRecuperar.Name = "TtucRecuperar";
			this.TtucRecuperar.Size = new System.Drawing.Size(180, 22);
			this.TtucRecuperar.Text = "TUC TUC";
			this.TtucRecuperar.Click += new System.EventHandler(TtucRecuperar_Click);
			this.EffectiveRecuperar.Name = "EffectiveRecuperar";
			this.EffectiveRecuperar.Size = new System.Drawing.Size(180, 22);
			this.EffectiveRecuperar.Text = "EFFECTIVE";
			this.EffectiveRecuperar.Click += new System.EventHandler(EffectiveRecuperar_Click);
			this.opcionesToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[8] { this.enviarEmailsToolStripMenuItem, this.imprimirPackingToolStripMenuItem, this.imprimirEtiquetasCajaToolStripMenuItem, this.generarEtiquetasEnvioToolStripMenuItem, this.modoECIToolStripMenuItem, this.modoVPToolStripMenuItem, this.configuraciónToolStripMenuItem, this.buscarActualizacionesToolStripMenuItem });
			this.opcionesToolStripMenuItem.Name = "opcionesToolStripMenuItem";
			this.opcionesToolStripMenuItem.Size = new System.Drawing.Size(69, 20);
			this.opcionesToolStripMenuItem.Text = "Opciones";
			this.enviarEmailsToolStripMenuItem.Name = "enviarEmailsToolStripMenuItem";
			this.enviarEmailsToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.enviarEmailsToolStripMenuItem.Text = "Enviar emails";
			this.enviarEmailsToolStripMenuItem.Click += new System.EventHandler(enviarEmailsToolStripMenuItem_Click);
			this.imprimirPackingToolStripMenuItem.Name = "imprimirPackingToolStripMenuItem";
			this.imprimirPackingToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.imprimirPackingToolStripMenuItem.Text = "Imprimir packing";
			this.imprimirPackingToolStripMenuItem.Click += new System.EventHandler(imprimirPackingToolStripMenuItem_Click);
			this.imprimirEtiquetasCajaToolStripMenuItem.Name = "imprimirEtiquetasCajaToolStripMenuItem";
			this.imprimirEtiquetasCajaToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.imprimirEtiquetasCajaToolStripMenuItem.Text = "Imprimir Etiquetas Caja";
			this.imprimirEtiquetasCajaToolStripMenuItem.Click += new System.EventHandler(imprimirEtiquetasCajaToolStripMenuItem_Click);
			this.generarEtiquetasEnvioToolStripMenuItem.Name = "generarEtiquetasEnvioToolStripMenuItem";
			this.generarEtiquetasEnvioToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.generarEtiquetasEnvioToolStripMenuItem.Text = "Generar etiquetas envio";
			this.generarEtiquetasEnvioToolStripMenuItem.Click += new System.EventHandler(generarEtiquetasEnvioToolStripMenuItem_Click);
			this.modoECIToolStripMenuItem.Name = "modoECIToolStripMenuItem";
			this.modoECIToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.modoECIToolStripMenuItem.Text = "Modo ECI";
			this.modoECIToolStripMenuItem.Click += new System.EventHandler(modoECIToolStripMenuItem_Click);
			this.modoVPToolStripMenuItem.Name = "modoVPToolStripMenuItem";
			this.modoVPToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.modoVPToolStripMenuItem.Text = "Modo VP";
			this.modoVPToolStripMenuItem.Click += new System.EventHandler(ModoVPToolStripMenuItem1_Click);
			this.configuraciónToolStripMenuItem.Name = "configuraciónToolStripMenuItem";
			this.configuraciónToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.configuraciónToolStripMenuItem.Text = "Ajustes";
			this.configuraciónToolStripMenuItem.Click += new System.EventHandler(configuraciónToolStripMenuItem_Click);
			this.buscarActualizacionesToolStripMenuItem.Name = "buscarActualizacionesToolStripMenuItem";
			this.buscarActualizacionesToolStripMenuItem.Size = new System.Drawing.Size(198, 22);
			this.buscarActualizacionesToolStripMenuItem.Text = "Buscar actualizaciones";
			this.buscarActualizacionesToolStripMenuItem.Click += new System.EventHandler(buscarActualizacionesToolStripMenuItem_Click);
			this.statusStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[6] { this.VersionLabel, this.toolStripStatusLabel1, this.serverIpLbl, this.toolStripStatusLabel2, this.databaseNameLbl, this.modeStatusLabel });
			this.statusStrip1.Location = new System.Drawing.Point(0, 659);
			this.statusStrip1.Name = "statusStrip1";
			this.statusStrip1.Size = new System.Drawing.Size(1008, 22);
			this.statusStrip1.SizingGrip = false;
			this.statusStrip1.TabIndex = 2;
			this.statusStrip1.Text = "statusStrip1";
			this.VersionLabel.Name = "VersionLabel";
			this.VersionLabel.Size = new System.Drawing.Size(13, 17);
			this.VersionLabel.Text = "v";
			this.VersionLabel.TextDirection = System.Windows.Forms.ToolStripTextDirection.Horizontal;
			this.toolStripStatusLabel1.Font = new System.Drawing.Font("Segoe UI", 9f, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, 0);
			this.toolStripStatusLabel1.Name = "toolStripStatusLabel1";
			this.toolStripStatusLabel1.Size = new System.Drawing.Size(48, 17);
			this.toolStripStatusLabel1.Text = "Server:";
			this.toolStripStatusLabel1.Visible = false;
			this.serverIpLbl.Name = "serverIpLbl";
			this.serverIpLbl.Size = new System.Drawing.Size(0, 17);
			this.toolStripStatusLabel2.Font = new System.Drawing.Font("Segoe UI", 9f, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, 0);
			this.toolStripStatusLabel2.Name = "toolStripStatusLabel2";
			this.toolStripStatusLabel2.Size = new System.Drawing.Size(61, 17);
			this.toolStripStatusLabel2.Text = "Database:";
			this.databaseNameLbl.Name = "databaseNameLbl";
			this.databaseNameLbl.Size = new System.Drawing.Size(0, 17);
			this.modeStatusLabel.Font = new System.Drawing.Font("Segoe UI", 9f, System.Drawing.FontStyle.Bold | System.Drawing.FontStyle.Italic, System.Drawing.GraphicsUnit.Point, 0);
			this.modeStatusLabel.Name = "modeStatusLabel";
			this.modeStatusLabel.Size = new System.Drawing.Size(82, 17);
			this.modeStatusLabel.Text = "Modo normal";
			this.panelScanPe.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
			this.panelScanPe.Controls.Add(this.modoVPGroupBox);
			this.panelScanPe.Controls.Add(this.label3);
			this.panelScanPe.Controls.Add(this.boxLblPrintTxt);
			this.panelScanPe.Controls.Add(this._shiftPausedTimeDisplay);
			this.panelScanPe.Controls.Add(this._shiftTotalTimeDisplay);
			this.panelScanPe.Controls.Add(this.shiftProductivityLabel);
			this.panelScanPe.Controls.Add(this.shiftScansLabel);
			this.panelScanPe.Controls.Add(this.pklTemporalTxt);
			this.panelScanPe.Controls.Add(this.label2);
			this.panelScanPe.Controls.Add(this.pklNoAcabadoTxt);
			this.panelScanPe.Controls.Add(this.label1);
			this.panelScanPe.Controls.Add(this.pendientesPedidoBox);
			this.panelScanPe.Controls.Add(this.pendientesPedidoLabel);
			this.panelScanPe.Controls.Add(this.nombreOleadaLbl);
			this.panelScanPe.Controls.Add(this.nombreOleadaTxt);
			this.panelScanPe.Controls.Add(this.timeRemainingLbl);
			this.panelScanPe.Controls.Add(this.filtroPendBtn);
			this.panelScanPe.Controls.Add(this.totalUnitsHourLbl);
			this.panelScanPe.Controls.Add(this.productivityBtn);
			this.panelScanPe.Controls.Add(this.pauseTimerBtn);
			this.panelScanPe.Controls.Add(this._totalElapsedTimeDisplay);
			this.panelScanPe.Controls.Add(this.pendingArticlesBtn);
			this.panelScanPe.Controls.Add(this.seqValueLbl);
			this.panelScanPe.Controls.Add(this.nextBoxBtn);
			this.panelScanPe.Controls.Add(this.newBoxTxt);
			this.panelScanPe.Controls.Add(this.nextBtn);
			this.panelScanPe.Controls.Add(this.scanInput);
			this.panelScanPe.Controls.Add(this.lblPe);
			this.panelScanPe.Location = new System.Drawing.Point(12, 27);
			this.panelScanPe.Name = "panelScanPe";
			this.panelScanPe.Size = new System.Drawing.Size(984, 338);
			this.panelScanPe.TabIndex = 1;
			this.modoVPGroupBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right;
			this.modoVPGroupBox.Controls.Add(this.palletNumBox);
			this.modoVPGroupBox.Controls.Add(this.rePrintVpLabelBox);
			this.modoVPGroupBox.Controls.Add(this.label4);
			this.modoVPGroupBox.Controls.Add(this.assignPaletBtn);
			this.modoVPGroupBox.Location = new System.Drawing.Point(585, 256);
			this.modoVPGroupBox.Name = "modoVPGroupBox";
			this.modoVPGroupBox.Size = new System.Drawing.Size(265, 79);
			this.modoVPGroupBox.TabIndex = 31;
			this.modoVPGroupBox.TabStop = false;
			this.modoVPGroupBox.Text = "Modo VP";
			this.palletNumBox.Location = new System.Drawing.Point(19, 17);
			this.palletNumBox.Name = "palletNumBox";
			this.palletNumBox.Size = new System.Drawing.Size(99, 20);
			this.palletNumBox.TabIndex = 35;
			this.rePrintVpLabelBox.Location = new System.Drawing.Point(124, 47);
			this.rePrintVpLabelBox.Name = "rePrintVpLabelBox";
			this.rePrintVpLabelBox.Size = new System.Drawing.Size(122, 20);
			this.rePrintVpLabelBox.TabIndex = 34;
			this.rePrintVpLabelBox.KeyDown += new System.Windows.Forms.KeyEventHandler(rePrintVpLabelBox_KeyDown);
			this.label4.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this.label4.AutoSize = true;
			this.label4.Location = new System.Drawing.Point(44, 50);
			this.label4.Name = "label4";
			this.label4.Size = new System.Drawing.Size(74, 13);
			this.label4.TabIndex = 33;
			this.label4.Text = "Num. Etiqueta";
			this.assignPaletBtn.Location = new System.Drawing.Point(124, 15);
			this.assignPaletBtn.Name = "assignPaletBtn";
			this.assignPaletBtn.Size = new System.Drawing.Size(122, 23);
			this.assignPaletBtn.TabIndex = 30;
			this.assignPaletBtn.Text = "Asignar bultos a pallet";
			this.assignPaletBtn.UseVisualStyleBackColor = true;
			this.assignPaletBtn.Click += new System.EventHandler(assignPaletBtn_Click);
			this.label3.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.label3.AutoSize = true;
			this.label3.Location = new System.Drawing.Point(844, 8);
			this.label3.Name = "label3";
			this.label3.Size = new System.Drawing.Size(51, 13);
			this.label3.TabIndex = 29;
			this.label3.Text = "Imp. Etiq.";
			this.boxLblPrintTxt.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.boxLblPrintTxt.Enabled = false;
			this.boxLblPrintTxt.Location = new System.Drawing.Point(847, 24);
			this.boxLblPrintTxt.Name = "boxLblPrintTxt";
			this.boxLblPrintTxt.Size = new System.Drawing.Size(39, 20);
			this.boxLblPrintTxt.TabIndex = 28;
			this.boxLblPrintTxt.KeyDown += new System.Windows.Forms.KeyEventHandler(boxLblPrintTxt_KeyDown);
			this._shiftPausedTimeDisplay.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this._shiftPausedTimeDisplay.AutoSize = true;
			this._shiftPausedTimeDisplay.Font = new System.Drawing.Font("Microsoft Sans Serif", 12f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
			this._shiftPausedTimeDisplay.Location = new System.Drawing.Point(4, 314);
			this._shiftPausedTimeDisplay.Name = "_shiftPausedTimeDisplay";
			this._shiftPausedTimeDisplay.Size = new System.Drawing.Size(93, 20);
			this._shiftPausedTimeDisplay.TabIndex = 27;
			this._shiftPausedTimeDisplay.Text = "Pausas (h): ";
			this._shiftTotalTimeDisplay.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this._shiftTotalTimeDisplay.AutoSize = true;
			this._shiftTotalTimeDisplay.Font = new System.Drawing.Font("Microsoft Sans Serif", 12f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
			this._shiftTotalTimeDisplay.Location = new System.Drawing.Point(4, 288);
			this._shiftTotalTimeDisplay.Name = "_shiftTotalTimeDisplay";
			this._shiftTotalTimeDisplay.Size = new System.Drawing.Size(98, 20);
			this._shiftTotalTimeDisplay.TabIndex = 26;
			this._shiftTotalTimeDisplay.Text = "Jornada (h): ";
			this.shiftProductivityLabel.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this.shiftProductivityLabel.AutoSize = true;
			this.shiftProductivityLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 12f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
			this.shiftProductivityLabel.Location = new System.Drawing.Point(5, 262);
			this.shiftProductivityLabel.Name = "shiftProductivityLabel";
			this.shiftProductivityLabel.Size = new System.Drawing.Size(102, 20);
			this.shiftProductivityLabel.TabIndex = 25;
			this.shiftProductivityLabel.Text = "U/h (turno): 0";
			this.shiftScansLabel.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this.shiftScansLabel.AutoSize = true;
			this.shiftScansLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 12f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
			this.shiftScansLabel.Location = new System.Drawing.Point(4, 236);
			this.shiftScansLabel.Name = "shiftScansLabel";
			this.shiftScansLabel.Size = new System.Drawing.Size(145, 20);
			this.shiftScansLabel.TabIndex = 24;
			this.shiftScansLabel.Text = "Unidades (turno): 0";
			this.pklTemporalTxt.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.pklTemporalTxt.Enabled = false;
			this.pklTemporalTxt.Location = new System.Drawing.Point(856, 215);
			this.pklTemporalTxt.Name = "pklTemporalTxt";
			this.pklTemporalTxt.Size = new System.Drawing.Size(125, 20);
			this.pklTemporalTxt.TabIndex = 23;
			this.pklTemporalTxt.KeyDown += new System.Windows.Forms.KeyEventHandler(pklTemporalTxt_KeyDown);
			this.label2.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.label2.AutoSize = true;
			this.label2.Location = new System.Drawing.Point(853, 197);
			this.label2.Name = "label2";
			this.label2.Size = new System.Drawing.Size(122, 13);
			this.label2.TabIndex = 22;
			this.label2.Text = "SEQ para PKL temporal:";
			this.pklNoAcabadoTxt.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.pklNoAcabadoTxt.Location = new System.Drawing.Point(856, 174);
			this.pklNoAcabadoTxt.Name = "pklNoAcabadoTxt";
			this.pklNoAcabadoTxt.Size = new System.Drawing.Size(125, 20);
			this.pklNoAcabadoTxt.TabIndex = 21;
			this.pklNoAcabadoTxt.KeyDown += new System.Windows.Forms.KeyEventHandler(pklNoAcabadoTxt_KeyDown);
			this.label1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.label1.AutoSize = true;
			this.label1.Location = new System.Drawing.Point(853, 156);
			this.label1.Name = "label1";
			this.label1.Size = new System.Drawing.Size(120, 13);
			this.label1.TabIndex = 20;
			this.label1.Text = "SEQ para FORZAR PE:";
			this.pendientesPedidoBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.pendientesPedidoBox.Enabled = false;
			this.pendientesPedidoBox.Location = new System.Drawing.Point(856, 256);
			this.pendientesPedidoBox.Name = "pendientesPedidoBox";
			this.pendientesPedidoBox.Size = new System.Drawing.Size(125, 20);
			this.pendientesPedidoBox.TabIndex = 19;
			this.pendientesPedidoBox.KeyDown += new System.Windows.Forms.KeyEventHandler(pendientesPedidoBox_KeyDown);
			this.pendientesPedidoLabel.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.pendientesPedidoLabel.AutoSize = true;
			this.pendientesPedidoLabel.Location = new System.Drawing.Point(853, 238);
			this.pendientesPedidoLabel.Name = "pendientesPedidoLabel";
			this.pendientesPedidoLabel.Size = new System.Drawing.Size(111, 13);
			this.pendientesPedidoLabel.TabIndex = 18;
			this.pendientesPedidoLabel.Text = "SEQ pendientes PDF:";
			this.nombreOleadaLbl.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.nombreOleadaLbl.AutoSize = true;
			this.nombreOleadaLbl.Location = new System.Drawing.Point(853, 115);
			this.nombreOleadaLbl.Name = "nombreOleadaLbl";
			this.nombreOleadaLbl.Size = new System.Drawing.Size(89, 13);
			this.nombreOleadaLbl.TabIndex = 17;
			this.nombreOleadaLbl.Text = "Nombre oleada: *";
			this.nombreOleadaTxt.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.nombreOleadaTxt.Location = new System.Drawing.Point(856, 133);
			this.nombreOleadaTxt.Name = "nombreOleadaTxt";
			this.nombreOleadaTxt.Size = new System.Drawing.Size(125, 20);
			this.nombreOleadaTxt.TabIndex = 16;
			this.nombreOleadaTxt.KeyDown += new System.Windows.Forms.KeyEventHandler(nombreOleadaTxt_KeyDown);
			this.timeRemainingLbl.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this.timeRemainingLbl.AutoSize = true;
			this.timeRemainingLbl.Location = new System.Drawing.Point(57, 55);
			this.timeRemainingLbl.Name = "timeRemainingLbl";
			this.timeRemainingLbl.Size = new System.Drawing.Size(68, 13);
			this.timeRemainingLbl.TabIndex = 15;
			this.timeRemainingLbl.Text = "Restante (h):";
			this.filtroPendBtn.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right;
			this.filtroPendBtn.Location = new System.Drawing.Point(856, 285);
			this.filtroPendBtn.Name = "filtroPendBtn";
			this.filtroPendBtn.Size = new System.Drawing.Size(125, 23);
			this.filtroPendBtn.TabIndex = 11;
			this.filtroPendBtn.Text = "FILTRO PEND.";
			this.toolTip1.SetToolTip(this.filtroPendBtn, "Mostrar/esconder artículos pendientes");
			this.filtroPendBtn.Click += new System.EventHandler(filtroPendBtn_Click);
			this.totalUnitsHourLbl.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this.totalUnitsHourLbl.AutoSize = true;
			this.totalUnitsHourLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 12f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
			this.totalUnitsHourLbl.Location = new System.Drawing.Point(4, 210);
			this.totalUnitsHourLbl.Name = "totalUnitsHourLbl";
			this.totalUnitsHourLbl.Size = new System.Drawing.Size(107, 20);
			this.totalUnitsHourLbl.TabIndex = 13;
			this.totalUnitsHourLbl.Text = "Ritmo (U/h): 0";
			this.productivityBtn.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left;
			this.productivityBtn.Image = PedidosMultiples.Properties.Resources.timer_restart_32x32;
			this.productivityBtn.Location = new System.Drawing.Point(3, 156);
			this.productivityBtn.Name = "productivityBtn";
			this.productivityBtn.Size = new System.Drawing.Size(45, 45);
			this.productivityBtn.TabIndex = 10;
			this.toolTip1.SetToolTip(this.productivityBtn, "Finalizar jornada");
			this.productivityBtn.UseVisualStyleBackColor = true;
			this.productivityBtn.Click += new System.EventHandler(productivityBtn_Click);
			this.pauseTimerBtn.Image = (System.Drawing.Image)resources.GetObject("pauseTimerBtn.Image");
			this.pauseTimerBtn.Location = new System.Drawing.Point(3, 23);
			this.pauseTimerBtn.Name = "pauseTimerBtn";
			this.pauseTimerBtn.Size = new System.Drawing.Size(45, 45);
			this.pauseTimerBtn.TabIndex = 9;
			this.toolTip1.SetToolTip(this.pauseTimerBtn, "Pausar tiempo");
			this.pauseTimerBtn.UseVisualStyleBackColor = true;
			this.pauseTimerBtn.Click += new System.EventHandler(pauseTimerBtn_Click);
			this._totalElapsedTimeDisplay.AutoSize = true;
			this._totalElapsedTimeDisplay.Font = new System.Drawing.Font("Microsoft Sans Serif", 20.25f, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, 0);
			this._totalElapsedTimeDisplay.Location = new System.Drawing.Point(54, 23);
			this._totalElapsedTimeDisplay.Name = "_totalElapsedTimeDisplay";
			this._totalElapsedTimeDisplay.Size = new System.Drawing.Size(128, 31);
			this._totalElapsedTimeDisplay.TabIndex = 8;
			this._totalElapsedTimeDisplay.Text = "00:00:00";
			this._totalElapsedTimeDisplay.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			this.pendingArticlesBtn.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right;
			this.pendingArticlesBtn.Enabled = false;
			this.pendingArticlesBtn.Location = new System.Drawing.Point(856, 312);
			this.pendingArticlesBtn.Name = "pendingArticlesBtn";
			this.pendingArticlesBtn.Size = new System.Drawing.Size(125, 23);
			this.pendingArticlesBtn.TabIndex = 7;
			this.pendingArticlesBtn.Text = "INFORME PEND.";
			this.toolTip1.SetToolTip(this.pendingArticlesBtn, "Crear PDF con artículos pendientes");
			this.pendingArticlesBtn.UseVisualStyleBackColor = true;
			this.pendingArticlesBtn.Click += new System.EventHandler(pendingArticlesBtn_Click);
			this.seqValueLbl.AutoSize = true;
			this.seqValueLbl.Font = new System.Drawing.Font("Microsoft Sans Serif", 12f, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, 0);
			this.seqValueLbl.Location = new System.Drawing.Point(5, 3);
			this.seqValueLbl.Name = "seqValueLbl";
			this.seqValueLbl.Size = new System.Drawing.Size(0, 20);
			this.seqValueLbl.TabIndex = 6;
			this.nextBoxBtn.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
			this.nextBoxBtn.Image = PedidosMultiples.Properties.Resources.changeBox;
			this.nextBoxBtn.Location = new System.Drawing.Point(901, 3);
			this.nextBoxBtn.Name = "nextBoxBtn";
			this.nextBoxBtn.Size = new System.Drawing.Size(80, 83);
			this.nextBoxBtn.TabIndex = 5;
			this.toolTip1.SetToolTip(this.nextBoxBtn, "Cambiar caja");
			this.nextBoxBtn.Click += new System.EventHandler(nextBoxBtn_Click);
			this.newBoxTxt.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right;
			this.newBoxTxt.Enabled = false;
			this.newBoxTxt.Location = new System.Drawing.Point(901, 92);
			this.newBoxTxt.Name = "newBoxTxt";
			this.newBoxTxt.Size = new System.Drawing.Size(80, 20);
			this.newBoxTxt.TabIndex = 4;
			this.newBoxTxt.KeyDown += new System.Windows.Forms.KeyEventHandler(newBoxTxt_KeyDown);
			this.nextBtn.Anchor = System.Windows.Forms.AnchorStyles.None;
			this.nextBtn.Image = (System.Drawing.Image)resources.GetObject("nextBtn.Image");
			this.nextBtn.Location = new System.Drawing.Point(470, 290);
			this.nextBtn.Name = "nextBtn";
			this.nextBtn.Size = new System.Drawing.Size(45, 45);
			this.nextBtn.TabIndex = 2;
			this.toolTip1.SetToolTip(this.nextBtn, "Escanear artículos");
			this.nextBtn.UseVisualStyleBackColor = true;
			this.nextBtn.Click += new System.EventHandler(nextBtn_Click);
			this.scanInput.Anchor = System.Windows.Forms.AnchorStyles.None;
			this.scanInput.Location = new System.Drawing.Point(404, 264);
			this.scanInput.Name = "scanInput";
			this.scanInput.Size = new System.Drawing.Size(175, 20);
			this.scanInput.TabIndex = 1;
			this.scanInput.KeyDown += new System.Windows.Forms.KeyEventHandler(scanInput_KeyDown);
			this.lblPe.Dock = System.Windows.Forms.DockStyle.Fill;
			this.lblPe.Font = new System.Drawing.Font("Microsoft Sans Serif", 72f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
			this.lblPe.Location = new System.Drawing.Point(0, 0);
			this.lblPe.Name = "lblPe";
			this.lblPe.Size = new System.Drawing.Size(984, 338);
			this.lblPe.TabIndex = 0;
			this.lblPe.Text = "ESCANEAR PEDIDOS";
			this.lblPe.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			this.panelTable.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
			this.panelTable.Controls.Add(this.articlesGrid);
			this.panelTable.Location = new System.Drawing.Point(12, 407);
			this.panelTable.Name = "panelTable";
			this.panelTable.Size = new System.Drawing.Size(984, 249);
			this.panelTable.TabIndex = 3;
			this.articlesGrid.AllowUserToAddRows = false;
			this.articlesGrid.AllowUserToDeleteRows = false;
			this.articlesGrid.AutoSizeColumnsMode = System.Windows.Forms.DataGridViewAutoSizeColumnsMode.Fill;
			this.articlesGrid.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
			this.articlesGrid.Dock = System.Windows.Forms.DockStyle.Fill;
			this.articlesGrid.Location = new System.Drawing.Point(0, 0);
			this.articlesGrid.MultiSelect = false;
			this.articlesGrid.Name = "articlesGrid";
			this.articlesGrid.ReadOnly = true;
			this.articlesGrid.Size = new System.Drawing.Size(984, 249);
			this.articlesGrid.TabIndex = 1;
			this.articlesGrid.CellDoubleClick += new System.Windows.Forms.DataGridViewCellEventHandler(articlesGrid_CellDoubleClick);
			this.articlesGrid.ColumnAdded += new System.Windows.Forms.DataGridViewColumnEventHandler(articlesGrid_ColumnAdded);
			this.progressBarTotal.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
			this.progressBarTotal.Location = new System.Drawing.Point(12, 371);
			this.progressBarTotal.Name = "progressBarTotal";
			this.progressBarTotal.Size = new System.Drawing.Size(984, 30);
			this.progressBarTotal.TabIndex = 10;
			this.progressBarTotal.Paint += new System.Windows.Forms.PaintEventHandler(progressBarTotal_Paint);
			base.AutoScaleDimensions = new System.Drawing.SizeF(6f, 13f);
			base.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
			base.ClientSize = new System.Drawing.Size(1008, 681);
			base.Controls.Add(this.progressBarTotal);
			base.Controls.Add(this.panelTable);
			base.Controls.Add(this.statusStrip1);
			base.Controls.Add(this.menuStrip1);
			base.Controls.Add(this.panelScanPe);
			base.Icon = (System.Drawing.Icon)resources.GetObject("$this.Icon");
			base.MainMenuStrip = this.menuStrip1;
			this.MinimumSize = new System.Drawing.Size(1024, 720);
			base.Name = "InitialForm";
			base.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen;
			this.Text = "Pedidos Multiples";
			base.WindowState = System.Windows.Forms.FormWindowState.Maximized;
			base.FormClosing += new System.Windows.Forms.FormClosingEventHandler(InitialForm_FormClosing);
			base.Load += new System.EventHandler(Form1_Load);
			this.menuStrip1.ResumeLayout(false);
			this.menuStrip1.PerformLayout();
			this.statusStrip1.ResumeLayout(false);
			this.statusStrip1.PerformLayout();
			this.panelScanPe.ResumeLayout(false);
			this.panelScanPe.PerformLayout();
			this.modoVPGroupBox.ResumeLayout(false);
			this.modoVPGroupBox.PerformLayout();
			this.panelTable.ResumeLayout(false);
			((System.ComponentModel.ISupportInitialize)this.articlesGrid).EndInit();
			base.ResumeLayout(false);
			base.PerformLayout();
		}
	}
}
