public record Contrato(Guid Id, string Numero, string Cliente, string Correo, DateOnly Renovacion, bool Cancelado);
public record Aviso(Guid ContratoId, string Destinatario, DateOnly Renovacion, int Dias);
public record Datos(List<Contrato> Contratos, List<Aviso> Avisos);

public static class Renovaciones
{
    public static void Evaluar(Datos datos, DateOnly hoy)
    {
        foreach (var contrato in datos.Contratos)
        {
            var dias = contrato.Renovacion.DayNumber - hoy.DayNumber;
            if (dias is not (30 or 7 or 1))
                continue;
            var aviso = new Aviso(contrato.Id, contrato.Correo, contrato.Renovacion, dias);
            if (!datos.Avisos.Contains(aviso))
                datos.Avisos.Add(aviso);
        }
    }
}
