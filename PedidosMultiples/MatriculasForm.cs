using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Media;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace PedidosMultiples
{
	// Modo matricula KOROSHI (EFFE).
	// - Preregistro: se lee el SEQ de una posicion y despues las matriculas (CJ...) de
	//   sus cajas, en el orden en que se usaran. Se puede cambiar de SEQ en cualquier momento.
	// - Dialogo (seqFijo != null): se lee una sola matricula para cerrar una caja de ese SEQ.
	public class MatriculasForm : Form
	{
		private readonly Dictionary<string, List<string>> matriculas;

		private readonly int seqLength;

		private readonly Func<string, string> validarSeq;

		private readonly Func<string, string> validarMatricula;

		private readonly Action guardar;

		private readonly string seqFijo;

		private string seqActual;

		private TextBox entrada;

		private Label lblSeq;

		private Label lblEstado;

		private ListBox lista;

		public string MatriculaLeida { get; private set; }

		// validarSeq y validarMatricula devuelven null si es correcto, o el texto del error.
		public MatriculasForm(Dictionary<string, List<string>> matriculas, int seqLength, Func<string, string> validarSeq, Func<string, string> validarMatricula, Action guardar, string seqFijo)
		{
			this.matriculas = matriculas;
			this.seqLength = seqLength;
			this.validarSeq = validarSeq;
			this.validarMatricula = validarMatricula;
			this.guardar = guardar;
			this.seqFijo = seqFijo;
			seqActual = seqFijo;
			CrearControles();
			RefrescarLista();
		}

		private void CrearControles()
		{
			Text = (seqFijo == null) ? "Matrículas por posición (SEQ)" : ("Matrícula para cerrar la caja - SEQ " + seqFijo);
			StartPosition = FormStartPosition.CenterParent;
			FormBorderStyle = FormBorderStyle.FixedDialog;
			MaximizeBox = false;
			MinimizeBox = false;
			ClientSize = new Size(700, (seqFijo == null) ? 560 : 230);
			Font = new Font("Microsoft Sans Serif", 14f);
			Label lblAyuda = new Label
			{
				Location = new Point(12, 9),
				Size = new Size(676, 50),
				Text = ((seqFijo == null) ? "Leer el SEQ de la posición y después sus matrículas, en orden de uso." : "Leer la matrícula de la caja.")
			};
			lblSeq = new Label
			{
				Location = new Point(12, 62),
				Size = new Size(676, 30),
				Font = new Font("Microsoft Sans Serif", 16f, FontStyle.Bold)
			};
			entrada = new TextBox
			{
				Location = new Point(12, 98),
				Size = new Size(676, 35),
				CharacterCasing = CharacterCasing.Upper
			};
			entrada.KeyDown += entrada_KeyDown;
			lblEstado = new Label
			{
				Location = new Point(12, 140),
				Size = new Size(676, 50)
			};
			Button btnCerrar = new Button
			{
				Text = ((seqFijo == null) ? "Cerrar" : "Cancelar"),
				Size = new Size(160, 40),
				DialogResult = DialogResult.Cancel
			};
			CancelButton = btnCerrar;
			Controls.Add(lblAyuda);
			Controls.Add(lblSeq);
			Controls.Add(entrada);
			Controls.Add(lblEstado);
			Controls.Add(btnCerrar);
			if (seqFijo == null)
			{
				lista = new ListBox
				{
					Location = new Point(12, 195),
					Size = new Size(676, 300),
					Font = new Font("Consolas", 12f)
				};
				Button btnBorrar = new Button
				{
					Text = "Borrar última del SEQ",
					Location = new Point(12, 508),
					Size = new Size(260, 40)
				};
				btnBorrar.Click += btnBorrar_Click;
				btnCerrar.Location = new Point(528, 508);
				Controls.Add(lista);
				Controls.Add(btnBorrar);
			}
			else
			{
				btnCerrar.Location = new Point(528, 185);
			}
			Shown += delegate
			{
				entrada.Select();
			};
		}

		private void entrada_KeyDown(object sender, KeyEventArgs e)
		{
			if (e.KeyCode == Keys.Return)
			{
				e.SuppressKeyPress = true;
				string texto = entrada.Text.Trim().ToUpperInvariant();
				entrada.Clear();
				Procesar(texto);
			}
		}

		private void Procesar(string texto)
		{
			if (texto.Length == 0)
			{
				return;
			}
			if (seqFijo == null && texto.Length == seqLength && texto.All(char.IsDigit))
			{
				string errorSeq = validarSeq(texto);
				if (errorSeq != null)
				{
					Error(errorSeq);
					return;
				}
				seqActual = texto;
				if (!matriculas.ContainsKey(seqActual))
				{
					matriculas.Add(seqActual, new List<string>());
				}
				Ok("SEQ " + seqActual + ": leer sus matrículas");
				RefrescarLista();
				return;
			}
			if (!Regex.IsMatch(texto, "^[A-Z]{2}[A-Z0-9]+$"))
			{
				Error("Lectura no válida: " + texto);
				return;
			}
			if (seqActual == null)
			{
				Error("Leer primero el SEQ de la posición");
				return;
			}
			foreach (KeyValuePair<string, List<string>> item in matriculas)
			{
				if (item.Value.Contains(texto))
				{
					Error(texto + " ya está asignada al SEQ " + item.Key);
					return;
				}
			}
			Cursor = Cursors.WaitCursor;
			string errorMatricula = validarMatricula(texto);
			Cursor = Cursors.Default;
			if (errorMatricula != null)
			{
				Error(texto + ": " + errorMatricula);
				return;
			}
			if (seqFijo != null)
			{
				MatriculaLeida = texto;
				DialogResult = DialogResult.OK;
				Close();
				return;
			}
			matriculas[seqActual].Add(texto);
			guardar();
			Ok(texto + " añadida al SEQ " + seqActual + " (" + matriculas[seqActual].Count + ")");
			RefrescarLista();
		}

		private void btnBorrar_Click(object sender, EventArgs e)
		{
			if (seqActual != null && matriculas.ContainsKey(seqActual) && matriculas[seqActual].Count > 0)
			{
				string borrada = matriculas[seqActual][matriculas[seqActual].Count - 1];
				matriculas[seqActual].RemoveAt(matriculas[seqActual].Count - 1);
				guardar();
				Ok(borrada + " borrada del SEQ " + seqActual);
				RefrescarLista();
			}
			entrada.Select();
		}

		private void RefrescarLista()
		{
			lblSeq.Text = (seqActual == null) ? "SEQ: (leer SEQ)" : ("SEQ: " + seqActual);
			if (lista == null)
			{
				return;
			}
			lista.Items.Clear();
			foreach (string seq in matriculas.Keys.OrderBy((string s) => s))
			{
				lista.Items.Add(((seq == seqActual) ? "> " : "  ") + seq + ": " + string.Join(", ", matriculas[seq]));
			}
		}

		private void Ok(string texto)
		{
			lblEstado.Text = texto;
			lblEstado.BackColor = Color.LightGreen;
			entrada.Select();
		}

		private void Error(string texto)
		{
			SystemSounds.Hand.Play();
			lblEstado.Text = texto;
			lblEstado.BackColor = Color.LightCoral;
			entrada.Select();
		}
	}
}
