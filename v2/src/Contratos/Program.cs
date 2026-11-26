using System.Diagnostics;
using System.Net.Http.Json;
using System.Net.Mail;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
var telemetria = Telemetria.Crear(Environment.GetEnvironmentVariable("APPLICATIONINSIGHTS_CONNECTION_STRING"));
if (telemetria is not null)
{
    app.Use(async (ctx, next) =>
    {
        var inicio = DateTimeOffset.UtcNow;
        var reloj = Stopwatch.StartNew();
        try { await next(); }
        finally { telemetria.Registrar(ctx.Request.Method, ctx.Request.Path, ctx.Response.StatusCode, reloj.Elapsed, inicio); }
    });
}
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
app.MapGet("/api/salud", () => Results.Ok(new
{
    estado = "ok",
    version = Environment.GetEnvironmentVariable("APP_VERSION") ?? "local",
    commit = Environment.GetEnvironmentVariable("APP_COMMIT_SHA") ?? "local"
}));
app.Run();
record Alta(string Numero, string Cliente, string Correo, DateOnly Renovacion);
sealed record Telemetria(string Clave, Uri Destino)
{
    static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(5) };
    public static Telemetria? Crear(string? cadena)
    {
        if (string.IsNullOrWhiteSpace(cadena)) return null;
        var partes = cadena.Split(';', StringSplitOptions.RemoveEmptyEntries)
            .Select(p => p.Split('=', 2))
            .Where(p => p.Length == 2)
            .ToDictionary(p => p[0].Trim(), p => p[1].Trim(), StringComparer.OrdinalIgnoreCase);
        return partes.TryGetValue("InstrumentationKey", out var ikey) && partes.TryGetValue("IngestionEndpoint", out var ep)
            ? new Telemetria(ikey, new Uri(ep.TrimEnd('/') + "/v2/track"))
            : null;
    }
    public void Registrar(string metodo, string ruta, int estado, TimeSpan duracion, DateTimeOffset inicio)
    {
        var carga = new[]
        {
            new
            {
                name = "Microsoft.ApplicationInsights.Request",
                time = inicio.ToString("O"),
                iKey = Clave,
                data = new
                {
                    baseType = "RequestData",
                    baseData = new
                    {
                        ver = 2,
                        id = Guid.NewGuid().ToString("N"),
                        name = $"{metodo} {ruta}",
                        duration = duracion.ToString(@"dd\.hh\:mm\:ss\.fffffff"),
                        responseCode = estado.ToString(),
                        success = estado < 400
                    }
                }
            }
        };
        _ = Http.PostAsJsonAsync(Destino, carga);
    }
}
