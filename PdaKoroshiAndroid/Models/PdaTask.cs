namespace PdaKoroshiAndroid.Models;

public sealed record PdaTask(
    string Order,
    string Ean,
    int Lineal,
    int TargetUnit,
    int ExpectedUnits);
