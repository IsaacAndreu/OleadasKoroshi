using PdaKoroshiAndroid.Services;

namespace PdaKoroshiAndroid;

public partial class MainPage : ContentPage
{
    private readonly PdaPickingSession session = new();

    public MainPage()
    {
        InitializeComponent();
        session.LoadDemoTasks();
        RefreshScreen("Preparado para la prova. Escaneja DEMO o usa el botó de prova.");
    }

    private void OnDemoScanClicked(object? sender, EventArgs e)
    {
        var result = session.ScanNextDemo();
        RefreshScreen(result.Message);
    }

    private void OnScanCompleted(object? sender, EventArgs e)
    {
        var value = ScanEntry.Text?.Trim() ?? string.Empty;
        ScanEntry.Text = string.Empty;
        if (value.Equals("DEMO", StringComparison.OrdinalIgnoreCase))
        {
            OnDemoScanClicked(sender, e);
            return;
        }

        var result = session.Scan(value);
        RefreshScreen(result.Message);
    }

    private void OnCloseBoxClicked(object? sender, EventArgs e)
    {
        var result = session.CloseCurrentBox();
        RefreshScreen(result.Message);
    }

    private void OnChangeBoxClicked(object? sender, EventArgs e)
    {
        var result = session.ChangeBox();
        RefreshScreen(result.Message);
    }

    private void OnResetClicked(object? sender, EventArgs e)
    {
        session.Reset();
        RefreshScreen("Prova reiniciada. No s'ha escrit res fora de l'app.");
    }

    private void RefreshScreen(string message)
    {
        var current = session.CurrentTask;
        OrderLabel.Text = current is null ? "Pedido: —" : $"Pedido: {current.Order}";
        DestinationLabel.Text = current is null ? "U —" : $"U{current.TargetUnit}";
        BoxLabel.Text = current is null ? "Caja: —" : $"Caja: {session.CurrentBoxCode}";
        ProgressLabel.Text = $"{session.ScannedUnits} / {session.TotalUnits} unitats · {session.ScannedTasks} lectures";
        StatusLabel.Text = message;
        StatusLabel.TextColor = message.StartsWith("ERROR", StringComparison.OrdinalIgnoreCase)
            ? Colors.DarkRed
            : Colors.DarkGreen;
    }
}
