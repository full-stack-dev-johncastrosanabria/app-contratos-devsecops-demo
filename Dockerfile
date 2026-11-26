FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
ARG APP_VERSION=v1
WORKDIR /src
COPY ${APP_VERSION}/src/Contratos/ ./Contratos/
RUN dotnet publish ./Contratos/Contratos.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
ARG APP_VERSION=v1
ARG GIT_SHA=unknown
WORKDIR /app
ENV ASPNETCORE_URLS=http://+:8080 \
    APP_VERSION=${APP_VERSION} \
    APP_COMMIT_SHA=${GIT_SHA}
COPY --from=build /app/publish .
EXPOSE 8080
ENTRYPOINT ["dotnet", "Contratos.dll"]
