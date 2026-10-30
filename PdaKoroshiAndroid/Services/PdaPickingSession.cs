using PdaKoroshiAndroid.Models;

namespace PdaKoroshiAndroid.Services;

public sealed class PdaPickingSession
{
    private readonly List<PdaTask> tasks = new();
    private readonly HashSet<string> scannedKeys = new(StringComparer.OrdinalIgnoreCase);
    private readonly HashSet<string> closedBoxes = new(StringComparer.OrdinalIgnoreCase);
    private int demoIndex;
    private int currentBoxNumber = 1;
    private int currentBoxUnits;

    public PdaTask? CurrentTask { get; private set; }
    public int ScannedUnits { get; private set; }
    public int ScannedTasks => scannedKeys.Count;
    public int TotalUnits => tasks.Sum(t => t.ExpectedUnits);
    public string CurrentBoxCode => $"DEMO-U{(CurrentTask?.TargetUnit ?? 1)}-C{currentBoxNumber:00}";

    public void LoadDemoTasks()
    {
        tasks.Clear();
        tasks.AddRange(new[]
        {
            new PdaTask("S-0001", "EAN-0001", 42, 1, 3),
            new PdaTask("S-0001", "EAN-0002", 43, 1, 2),
            new PdaTask("S-0002", "EAN-0003", 78, 2, 4),
            new PdaTask("S-0003", "EAN-0004", 101, 3, 1),
            new PdaTask("S-0004", "EAN-0005", 121, 4, 5),
            new PdaTask("S-0005", "EAN-0006", 133, 5, 2)
        });
        Reset();
    }

    public PdaScanResult ScanNextDemo()
    {
        if (demoIndex >= tasks.Count)
            return new(false, "ERROR: no queden lectures de prova.");

        var task = tasks[demoIndex++];
        return Scan(task.Ean);
    }

    public PdaScanResult Scan(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return new(false, "ERROR: lectura buida.");

        var task = tasks.FirstOrDefault(t => t.Ean.Equals(value, StringComparison.OrdinalIgnoreCase));
        if (task is null)
            return new(false, $"ERROR: EAN {value} no està en la prova.");

        var key = $"{task.Order}|{task.Ean}|{task.TargetUnit}";
        if (!scannedKeys.Add(key))
            return new(false, $"ERROR: lectura duplicada de {task.Order} / U{task.TargetUnit}.");

        CurrentTask = task;
        currentBoxUnits++;
        ScannedUnits++;
        return new(true, $"OK: {task.Order} → U{task.TargetUnit}, lineal L{task.Lineal:00}.");
    }

    public PdaScanResult CloseCurrentBox()
    {
        if (currentBoxUnits == 0)
            return new(false, "ERROR: no es pot tancar una caixa buida.");

        var code = CurrentBoxCode;
        if (!closedBoxes.Add(code))
            return new(false, $"ERROR: la caixa {code} ja està tancada.");

        currentBoxUnits = 0;
        currentBoxNumber++;
        return new(true, $"OK: caixa {code} tancada.");
    }

    public PdaScanResult ChangeBox()
    {
        var result = CloseCurrentBox();
        if (!result.IsOk)
            return result;

        return new(true, result.Message + " Escaneja la següent peça.");
    }

    public void Reset()
    {
        scannedKeys.Clear();
        closedBoxes.Clear();
        demoIndex = 0;
        currentBoxNumber = 1;
        currentBoxUnits = 0;
        ScannedUnits = 0;
        CurrentTask = null;
    }
}
