using System.Net.Mail;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var archivo = Path.Combine(app.Environment.ContentRootPath, "datos.json");
var puerta = new object();
Datos Leer() => File.Exists(archivo)
    ? JsonSerializer.Deserialize<Datos>(File.ReadAllText(archivo)) ?? throw new InvalidDataException()
    : new Datos([], []);

IResult Cambiar(Func<Datos, IResult> accion)
{
    lock (puerta)
    {
        var datos = Leer();
        var respuesta = accion(datos);
        if (respuesta is IStatusCodeHttpResult { StatusCode: >= 400 })
            return respuesta;
        File.WriteAllText(archivo + ".tmp", JsonSerializer.Serialize(datos));
        File.Move(archivo + ".tmp", archivo, true);
        return respuesta;
    }
}

app.UseDefaultFiles();
app.UseStaticFiles();
app.MapGet("/api/contratos", () => { lock (puerta) return Leer(); });
app.MapPost("/api/contratos", (Alta alta) => Cambiar(datos =>
{
    if (string.IsNullOrWhiteSpace(alta.Numero) || string.IsNullOrWhiteSpace(alta.Cliente)
        || !MailAddress.TryCreate(alta.Correo, out _) || alta.Renovacion == default)
        return Results.BadRequest("Revisá los datos del contrato.");
    var numero = alta.Numero.Trim();
    if (datos.Contratos.Any(c => c.Numero.Equals(numero, StringComparison.OrdinalIgnoreCase)))
        return Results.Conflict("Ese número de contrato ya existe.");
    var contrato = new Contrato(Guid.NewGuid(), numero, alta.Cliente.Trim(), alta.Correo.Trim(), alta.Renovacion, false);
    datos.Contratos.Add(contrato);
    return Results.Ok(contrato);
}));
app.MapPost("/api/contratos/{id:guid}/cancelar", (Guid id) => Cambiar(datos =>
{
    var pos = datos.Contratos.FindIndex(c => c.Id == id);
    if (pos < 0) return Results.NotFound();
    datos.Contratos[pos] = datos.Contratos[pos] with { Cancelado = true };
    return Results.Ok();
}));
app.MapPost("/api/evaluar", (DateOnly? fecha) => fecha is null || fecha == default
    ? Results.BadRequest("Indicá una fecha de evaluación válida.")
    : Cambiar(datos =>
    {
        Renovaciones.Evaluar(datos, fecha.Value);
        return Results.Ok(datos.Avisos);
    }));
app.Run();
record Alta(string Numero, string Cliente, string Correo, DateOnly Renovacion);
