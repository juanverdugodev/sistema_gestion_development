# 🗄️ Gestión de Base de Datos

Para levantar el contenedor desde la raíz del proyecto (`sistema_gestion/`), asegurarse de tener abierto **Docker desktop para Windows** y ejecutar el siguiente comando en la terminal (CMD):

```cmd
docker run -d --name mysql_sistema_gestion --restart unless-stopped -p 3307:3306 -e MYSQL_ROOT_PASSWORD=Ro0t@4dmin26 -e TZ="America/Guayaquil" -v "%cd%\vol-data:/var/lib/mysql" -v "%cd%\db-sistema.sql:/docker-entrypoint-initdb.d/init.sql" mysql:8.0.36
```

> [!IMPORTANT]
> La versión de MySQL está fijada en 8.0.36 para garantizar la compatibilidad de los datos binarios entre diferentes equipos.

> [!NOTE]
> Se utiliza el puerto 3307 para evitar conflictos si ya existe MySQL instalado localmente en el puerto 3306.

> [!CAUTION]
> **Nunca subir el contenido de `vol-data/` al repositorio.**
> Esta carpeta contiene archivos binarios internos específicos de cada máquina. Revisar el archivo [.gitignore](../.gitignore).

