using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Printing;
using System.IO;
using System.Speech.Synthesis;
using System.Windows.Forms;
using ExcelDataReader;

namespace PedidosMultiples
{
	public class Configuracion : Form
	{
		private bool crmLogsValue;

		private IContainer components;

		private Label label1;

		private Label label2;

		private ComboBox emailPackingCbo;

		private ComboBox labelPrintCbo;

		private GroupBox groupBox1;

		private ComboBox voiceCbo;

		private Label label9;

		private CheckBox crmLogsChk;

		private Label label10;

		private ComboBox smallLabelCbo;

		private ComboBox pklCbo;

		private Label label3;

		public Configuracion()
		{
			InitializeComponent();
			AddInstalledVoicesToList();
			LoadEmailsFromExcel();
			SetLabelPrinterComboBoxIndex(labelPrintCbo);
			SetLabelPrinterComboBoxIndex(smallLabelCbo);
			SetLabelPrinterComboBoxIndex(pklCbo);
			voiceCbo.SelectedItem = InitialForm.ReturnSetting("voice");
			crmLogsChk.Checked = Convert.ToBoolean(InitialForm.ReturnSetting("crm_logs"));
			labelPrintCbo.SelectedItem = InitialForm.ReturnSetting("imp_tick");
			pklCbo.SelectedItem = InitialForm.ReturnSetting("imp_pack");
			smallLabelCbo.SelectedItem = InitialForm.ReturnSetting("imp_tick_small");
			emailPackingCbo.SelectedItem = InitialForm.ReturnSetting("email_pack");
		}

		private void AddInstalledVoicesToList()
		{
			using (SpeechSynthesizer synth = new SpeechSynthesizer())
			{
				foreach (InstalledVoice voice in synth.GetInstalledVoices())
				{
					voiceCbo.Items.Add(voice.VoiceInfo.Name);
				}
			}
		}

		private void crmLogsChk_CheckedChanged(object sender, EventArgs e)
		{
			crmLogsValue = Convert.ToBoolean(crmLogsChk.Checked.ToString());
			InitialForm.SetCrmLogs(crmLogsValue);
			InitialForm.AddUpdateAppSettings("crm_logs", crmLogsChk.Checked.ToString());
		}

		private void voiceCbo_SelectedIndexChanged(object sender, EventArgs e)
		{
			string voice = voiceCbo.Text;
			InitialForm.AddUpdateAppSettings("voice", voice);
		}

		private List<string> GetSystemPrinters()
		{
			List<string> printers = new List<string>();
			foreach (string printer in PrinterSettings.InstalledPrinters)
			{
				printers.Add(printer);
			}
			return printers;
		}

		private void SetLabelPrinterComboBoxIndex(ComboBox comboBox)
		{
			foreach (string item in GetSystemPrinters())
			{
				comboBox.Items.Add(item);
			}
		}

		private void labelPrintCbo_SelectedIndexChanged(object sender, EventArgs e)
		{
			InitialForm.AddUpdateAppSettings("imp_tick", labelPrintCbo.SelectedItem.ToString());
		}

		private void pklCbo_SelectedIndexChanged(object sender, EventArgs e)
		{
			InitialForm.AddUpdateAppSettings("imp_pack", pklCbo.SelectedItem.ToString());
		}

		private void smallLabelCbo_SelectedIndexChanged(object sender, EventArgs e)
		{
			InitialForm.AddUpdateAppSettings("imp_tick_small", smallLabelCbo.SelectedItem.ToString());
		}

		private void LoadEmailsFromExcel()
		{
			try
			{
				string directoryName = Path.GetDirectoryName(Application.ExecutablePath);
				string fileName = "MerchandizersMails.xlsx";
				string filePath = Path.Combine(directoryName, fileName);
				if (!File.Exists(filePath))
				{
					MessageBox.Show("El archivo " + fileName + " no existe!", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				}
				else
				{
					using (FileStream stream = File.Open(filePath, FileMode.Open, FileAccess.Read))
					{
						using (IExcelDataReader reader = ExcelReaderFactory.CreateReader(stream, new ExcelReaderConfiguration
						{
							Password = "b@rç@"
						}))
						{
							while (true)
							{
								if (reader.Read())
								{
									if (!reader.GetString(1).Equals("Mail"))
									{
										emailPackingCbo.Items.Add(reader.GetString(1));
									}
								}
								else if (!reader.NextResult())
								{
									break;
								}
							}
						}
					}
				}
				if (!InitialForm.ReturnSetting("email_pack").Equals(null))
				{
					emailPackingCbo.SelectedIndex = emailPackingCbo.FindString(InitialForm.ReturnSetting("email_pack").ToString());
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void emailPackingCbo_SelectedIndexChanged(object sender, EventArgs e)
		{
			InitialForm.AddUpdateAppSettings("email_pack", emailPackingCbo.SelectedItem.ToString());
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
			this.label1 = new System.Windows.Forms.Label();
			this.label2 = new System.Windows.Forms.Label();
			this.emailPackingCbo = new System.Windows.Forms.ComboBox();
			this.labelPrintCbo = new System.Windows.Forms.ComboBox();
			this.groupBox1 = new System.Windows.Forms.GroupBox();
			this.pklCbo = new System.Windows.Forms.ComboBox();
			this.label3 = new System.Windows.Forms.Label();
			this.crmLogsChk = new System.Windows.Forms.CheckBox();
			this.label10 = new System.Windows.Forms.Label();
			this.smallLabelCbo = new System.Windows.Forms.ComboBox();
			this.voiceCbo = new System.Windows.Forms.ComboBox();
			this.label9 = new System.Windows.Forms.Label();
			this.groupBox1.SuspendLayout();
			base.SuspendLayout();
			this.label1.AutoSize = true;
			this.label1.Location = new System.Drawing.Point(7, 30);
			this.label1.Name = "label1";
			this.label1.Size = new System.Drawing.Size(99, 13);
			this.label1.TabIndex = 2;
			this.label1.Text = "Impresora etiquetas";
			this.label2.AutoSize = true;
			this.label2.Location = new System.Drawing.Point(7, 90);
			this.label2.Name = "label2";
			this.label2.Size = new System.Drawing.Size(55, 13);
			this.label2.TabIndex = 3;
			this.label2.Text = "Email PKL";
			this.emailPackingCbo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
			this.emailPackingCbo.FormattingEnabled = true;
			this.emailPackingCbo.Location = new System.Drawing.Point(10, 106);
			this.emailPackingCbo.Name = "emailPackingCbo";
			this.emailPackingCbo.Size = new System.Drawing.Size(135, 21);
			this.emailPackingCbo.TabIndex = 4;
			this.emailPackingCbo.SelectedIndexChanged += new System.EventHandler(emailPackingCbo_SelectedIndexChanged);
			this.labelPrintCbo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
			this.labelPrintCbo.FormattingEnabled = true;
			this.labelPrintCbo.Location = new System.Drawing.Point(10, 46);
			this.labelPrintCbo.Name = "labelPrintCbo";
			this.labelPrintCbo.Size = new System.Drawing.Size(135, 21);
			this.labelPrintCbo.TabIndex = 5;
			this.labelPrintCbo.SelectedIndexChanged += new System.EventHandler(labelPrintCbo_SelectedIndexChanged);
			this.groupBox1.Controls.Add(this.pklCbo);
			this.groupBox1.Controls.Add(this.label3);
			this.groupBox1.Controls.Add(this.crmLogsChk);
			this.groupBox1.Controls.Add(this.label10);
			this.groupBox1.Controls.Add(this.smallLabelCbo);
			this.groupBox1.Controls.Add(this.voiceCbo);
			this.groupBox1.Controls.Add(this.label9);
			this.groupBox1.Controls.Add(this.label1);
			this.groupBox1.Controls.Add(this.labelPrintCbo);
			this.groupBox1.Controls.Add(this.emailPackingCbo);
			this.groupBox1.Controls.Add(this.label2);
			this.groupBox1.Location = new System.Drawing.Point(12, 12);
			this.groupBox1.Name = "groupBox1";
			this.groupBox1.Size = new System.Drawing.Size(314, 237);
			this.groupBox1.TabIndex = 21;
			this.groupBox1.TabStop = false;
			this.groupBox1.Text = "Ajustes generales";
			this.pklCbo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
			this.pklCbo.DropDownWidth = 200;
			this.pklCbo.FormattingEnabled = true;
			this.pklCbo.Location = new System.Drawing.Point(166, 106);
			this.pklCbo.Name = "pklCbo";
			this.pklCbo.Size = new System.Drawing.Size(135, 21);
			this.pklCbo.TabIndex = 14;
			this.pklCbo.SelectedIndexChanged += new System.EventHandler(pklCbo_SelectedIndexChanged);
			this.label3.AutoSize = true;
			this.label3.Location = new System.Drawing.Point(163, 90);
			this.label3.Name = "label3";
			this.label3.Size = new System.Drawing.Size(76, 13);
			this.label3.TabIndex = 13;
			this.label3.Text = "Impresora PKL";
			this.crmLogsChk.AutoSize = true;
			this.crmLogsChk.Location = new System.Drawing.Point(166, 166);
			this.crmLogsChk.Name = "crmLogsChk";
			this.crmLogsChk.Size = new System.Drawing.Size(102, 17);
			this.crmLogsChk.TabIndex = 8;
			this.crmLogsChk.Text = "Inserts CRM DB";
			this.crmLogsChk.UseVisualStyleBackColor = true;
			this.crmLogsChk.CheckedChanged += new System.EventHandler(crmLogsChk_CheckedChanged);
			this.label10.AutoSize = true;
			this.label10.Location = new System.Drawing.Point(163, 30);
			this.label10.Name = "label10";
			this.label10.Size = new System.Drawing.Size(130, 13);
			this.label10.TabIndex = 6;
			this.label10.Text = "Impresora etiquetas Zebra";
			this.smallLabelCbo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
			this.smallLabelCbo.FormattingEnabled = true;
			this.smallLabelCbo.Location = new System.Drawing.Point(166, 46);
			this.smallLabelCbo.Name = "smallLabelCbo";
			this.smallLabelCbo.Size = new System.Drawing.Size(135, 21);
			this.smallLabelCbo.TabIndex = 7;
			this.smallLabelCbo.SelectedIndexChanged += new System.EventHandler(smallLabelCbo_SelectedIndexChanged);
			this.voiceCbo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
			this.voiceCbo.FormattingEnabled = true;
			this.voiceCbo.Location = new System.Drawing.Point(10, 166);
			this.voiceCbo.Name = "voiceCbo";
			this.voiceCbo.Size = new System.Drawing.Size(135, 21);
			this.voiceCbo.TabIndex = 1;
			this.voiceCbo.SelectedIndexChanged += new System.EventHandler(voiceCbo_SelectedIndexChanged);
			this.label9.AutoSize = true;
			this.label9.Location = new System.Drawing.Point(7, 150);
			this.label9.Name = "label9";
			this.label9.Size = new System.Drawing.Size(48, 13);
			this.label9.TabIndex = 0;
			this.label9.Text = "Tipo voz";
			base.AutoScaleDimensions = new System.Drawing.SizeF(6f, 13f);
			base.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
			base.ClientSize = new System.Drawing.Size(339, 261);
			base.Controls.Add(this.groupBox1);
			base.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;
			base.MaximizeBox = false;
			base.MinimizeBox = false;
			base.Name = "Configuracion";
			base.ShowIcon = false;
			base.ShowInTaskbar = false;
			base.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent;
			this.Text = "Ajustes";
			base.TopMost = true;
			this.groupBox1.ResumeLayout(false);
			this.groupBox1.PerformLayout();
			base.ResumeLayout(false);
		}
	}
}
