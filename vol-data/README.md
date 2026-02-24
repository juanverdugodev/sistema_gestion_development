# 🗄️ Gestión de Base de Datos

Para levantar el contenedor desde la raíz del proyecto (`sistema_gestion/`), asegurarse de tener abierto **Docker desktop para Windows** y ejecutar el siguiente comando en la terminal (CMD):

```cmd
docker run -d --name mysql_sistema_gestion --restart unless-stopped -p 3307:3306 -e MYSQL_ROOT_PASSWORD=Ro0t@4dmin26 -e MYSQL_DATABASE=sistema_gestion_db -e MYSQL_USER=app_user -e MYSQL_PASSWORD=AppP4ssw0rd26 -v "%cd%\vol-data:/var/lib/mysql" mysql:8.0.36
```

> [!IMPORTANT]
> La versión de MySQL está fijada en 8.0.36 para garantizar la compatibilidad de los datos binarios entre diferentes equipos.

> [!NOTE]
> Se utiliza el puerto 3307 para evitar conflictos si ya existe MySQL instalado localmente en el puerto 3306.

> [!CAUTION]
> **Nunca subir el contenido de `vol-data/` al repositorio.**
> Esta carpeta contiene archivos binarios internos específicos de cada máquina. Revisar el archivo [.gitignore](../.gitignore).

