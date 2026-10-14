using System;
using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;

namespace PedidosMultiples
{
	public class Form1 : Form
	{
		private string pedido;

		private string referencia;

		private string talla;

		private string color;

		private string productCode;

		private string cantidadEsperada;

		private string cantidadIntroducida;

		private int cantidadRestante;

		private int index;

		private IContainer components;

		private Label label2;

		private TextBox eanTxtBox;

		private Label label3;

		private TextBox qtyTxtBox;

		private Label pedidoLbl;

		private TextBox pedidoTxtBox;

		public Form1(string pe, string style, string size, string colour, string pCode, string qtyEsperada, string qtyLeida, int rowIndex)
		{
			InitializeComponent();
			pedido = pe;
			referencia = style;
			talla = size;
			color = colour;
			productCode = pCode;
			cantidadEsperada = qtyEsperada;
			cantidadIntroducida = qtyLeida;
			index = rowIndex;
			pedidoTxtBox.Text = pedido;
			eanTxtBox.Text = productCode;
			cantidadRestante = Convert.ToInt32(cantidadEsperada) - Convert.ToInt32(cantidadIntroducida);
			label3.Text = "Cantidad(esp: " + cantidadEsperada + ", rest: " + cantidadRestante + ")";
			qtyTxtBox.Select();
		}

		private void action()
		{
			try
			{
				cantidadIntroducida = qtyTxtBox.Text.ToString().Trim();
				if (cantidadIntroducida.Length > 0 && int.TryParse(cantidadIntroducida, out var _) && Convert.ToInt32(cantidadIntroducida) <= Convert.ToInt32(cantidadEsperada) && Convert.ToInt32(cantidadIntroducida) <= cantidadRestante)
				{
					((InitialForm)base.Owner).NotifyParentForm(pedido, referencia, talla, color, productCode, cantidadIntroducida, index);
					Close();
				}
				else
				{
					MessageBox.Show("Error en los datos introducidos!", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				}
			}
			catch (Exception ex)
			{
				MessageBox.Show(ex?.ToString() ?? "", "Error", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			}
		}

		private void qtyTxtBox_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Escape)
			{
				e.SuppressKeyPress = true;
				Close();
			}
			else if (e.KeyCode == Keys.Return)
			{
				e.SuppressKeyPress = true;
				action();
				qtyTxtBox.Text = null;
				qtyTxtBox.Select();
			}
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
			this.label2 = new System.Windows.Forms.Label();
			this.eanTxtBox = new System.Windows.Forms.TextBox();
			this.label3 = new System.Windows.Forms.Label();
			this.qtyTxtBox = new System.Windows.Forms.TextBox();
			this.pedidoLbl = new System.Windows.Forms.Label();
			this.pedidoTxtBox = new System.Windows.Forms.TextBox();
			base.SuspendLayout();
			this.label2.AutoSize = true;
			this.label2.Location = new System.Drawing.Point(117, 9);
			this.label2.Name = "label2";
			this.label2.Size = new System.Drawing.Size(74, 13);
			this.label2.TabIndex = 1;
			this.label2.Text = "Product_code";
			this.eanTxtBox.Location = new System.Drawing.Point(120, 25);
			this.eanTxtBox.Name = "eanTxtBox";
			this.eanTxtBox.ReadOnly = true;
			this.eanTxtBox.Size = new System.Drawing.Size(123, 20);
			this.eanTxtBox.TabIndex = 2;
			this.label3.AutoSize = true;
			this.label3.Location = new System.Drawing.Point(246, 9);
			this.label3.Name = "label3";
			this.label3.Size = new System.Drawing.Size(127, 13);
			this.label3.TabIndex = 3;
			this.label3.Text = "Cantidad (esp: X , rest: Y)";
			this.qtyTxtBox.Location = new System.Drawing.Point(249, 25);
			this.qtyTxtBox.Name = "qtyTxtBox";
			this.qtyTxtBox.Size = new System.Drawing.Size(124, 20);
			this.qtyTxtBox.TabIndex = 4;
			this.qtyTxtBox.KeyDown += new System.Windows.Forms.KeyEventHandler(qtyTxtBox_KeyDown);
			this.pedidoLbl.AutoSize = true;
			this.pedidoLbl.Location = new System.Drawing.Point(12, 9);
			this.pedidoLbl.Name = "pedidoLbl";
			this.pedidoLbl.Size = new System.Drawing.Size(40, 13);
			this.pedidoLbl.TabIndex = 6;
			this.pedidoLbl.Text = "Pedido";
			this.pedidoTxtBox.Location = new System.Drawing.Point(12, 25);
			this.pedidoTxtBox.Name = "pedidoTxtBox";
			this.pedidoTxtBox.ReadOnly = true;
			this.pedidoTxtBox.Size = new System.Drawing.Size(102, 20);
			this.pedidoTxtBox.TabIndex = 7;
			base.AutoScaleDimensions = new System.Drawing.SizeF(6f, 13f);
			base.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
			base.ClientSize = new System.Drawing.Size(384, 86);
			base.Controls.Add(this.pedidoTxtBox);
			base.Controls.Add(this.pedidoLbl);
			base.Controls.Add(this.qtyTxtBox);
			base.Controls.Add(this.label3);
			base.Controls.Add(this.eanTxtBox);
			base.Controls.Add(this.label2);
			base.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;
			base.MaximizeBox = false;
			this.MaximumSize = new System.Drawing.Size(400, 125);
			base.MinimizeBox = false;
			this.MinimumSize = new System.Drawing.Size(400, 125);
			base.Name = "Form1";
			base.ShowIcon = false;
			base.ShowInTaskbar = false;
			base.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent;
			this.Text = "Entrada manual";
			base.ResumeLayout(false);
			base.PerformLayout();
		}
	}
}
