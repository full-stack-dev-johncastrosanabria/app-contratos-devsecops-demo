using Xunit;
public class RenovacionesTests
{
    static readonly DateOnly Hoy = new(2026, 11, 26);
    static Datos Caso(bool cancelado, int dias) => new(
        [new Contrato(Guid.NewGuid(), "C-001", "Demo", "qa@example.com", Hoy.AddDays(dias), cancelado)], []);

    [Theory]
    [InlineData(30)]
    [InlineData(7)]
    [InlineData(1)]
    public void ActivoGeneraUnSoloAviso(int dias)
    {
        var datos = Caso(false, dias);
        Renovaciones.Evaluar(datos, Hoy);
        Renovaciones.Evaluar(datos, Hoy);
        Assert.Single(datos.Avisos);
    }

}
