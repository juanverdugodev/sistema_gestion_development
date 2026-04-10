# Sistema de gestión
Plataforma de alto rendimiento orientada a la automatización, procesamiento y validación de registros biométricos. Integra un motor de aprendizaje no supervisado **(K-Means)** y un sistema de persistencia basado en **Apache Parquet** óptimo para grandes volúmenes de datos.

## Demostración de funcionalidades

<div align="center">
  <a href="https://drive.google.com/file/d/1fbO9E8cG_cBjxrUoT22787Nit7q00tfy/view?usp=sharing" target="_blank">
    <img src="https://github.com/user-attachments/assets/b351ad90-e80c-4769-804e-0b46aa25ce05" alt="Ver demostración" width="100%" />
  </a>
</div>

## Interfaz del sistema
Vistas de los módulos del sistema.

<div align="center">
  <img src="https://github.com/user-attachments/assets/a0bcfdc6-0271-476f-9b74-ff3d14ff4374" alt="Login" width="100%" />
  <br><em><b>Inicio de sesión</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/a0db8638-b3ce-4c65-be39-8b3a18bcb12c" alt="Dashboard" width="100%" />
  <br><em><b>Panel principal</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/33b99890-df9a-4727-a711-5d1cd3aadcef" alt="Carga de registros" width="100%" />
  <br><em><b>Carga de registros</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/dc31eb8d-bc8c-4661-a56a-448a985e1f0d" alt="Vista previa de registros" width="100%" />
  <br><em><b>Vista previa de registros</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/f313d9f3-5fb5-4ad7-bfe8-01cf3823ed80" alt="Auditoria de registros" width="100%" />
  <br><em><b>Auditoria de registros</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/b59e0416-1f7f-40c2-ad11-5a342d147b65" alt="Validación de marcaciones" width="100%" />
  <br><em><b>Validación de marcaciones</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/e31e8576-2260-4176-a198-08eaa98e67d5" alt="Reportes" width="100%" />
  <br><em><b>Generación de reportes</b></em>
</div>

<br><br>

<div align="center">
  <img src="https://github.com/user-attachments/assets/3a715d66-e473-4d0a-a8db-dd9198a5a4e0" alt="Auditoria de logs" width="100%" />
  <br><em><b>Auditoria de logs</b></em>
</div>

---


## Índice
 1. [Arquitectura del sistema](#arquitectura-del-sistema)
 2. [Estructura del proyecto](#estructura-del-proyecto)
 3. [Arquitectura de datos (ETL)](#arquitectura-de-datos-etl)
 4. [Motor de machine learning](#motor-de-machine-learning)
 5. [Infraestructura y despliegue (Docker)](#infraestructura-y-despliegue-docker)
 6. [Base de datos MYSQL](#base-de-datos-mysql)
 7. [Stack tecnológico](#stack-tecnológico)
 8. [Colaboradores](#colaboradores)

## Arquitectura del sistema
El sistema sigue una arquitectura modular desacoplada basada en capas para garantizar la escalabilidad y el mantenimiento:
 * **Capa de presentación:** Templates y recursos estáticos.
 * **Capa de enrutamiento:** Definición de endpoints y gestión de peticiones (routers).
 * **Capa de lógica:** Controllers y procesamiento analítico.
 * **Capa de utilidades:** Funciones auxiliares y motores especializados.
 * **Capa de persistencia:** Archivos Parquet de alto rendimiento como base de datos.

## Estructura del proyecto
La organización del código está diseñada para mantener la separación de responsabilidades. A continuación se detalla la arquitectura de directorio y archivos importantes del proyecto:

```
sistema/
|
├── app/
│   ├── controllers/    # Backend y validaciones
|   |   ├── admin_controller.py     # Lógica del panel de administrador
|   |   ├── auth_controller.py      # Lógica de login
|   |   ├── export_xlsx_controller      # Lógica del panel de exportación de xlsx
|   |   ├── logs_controller.py      # Lógica del panel de logs
|   |   ├── password_controller.py      # Lógica del cambio de clave
|   |   ├── profile_controller.py   # Lógica para perfil usuario
|   |   ├── upload_xlsx_controller.py   # Lógica del panel de carga de datos
|   |   └── user_mark_day_records_controller.py     # Lógica de panel de busqueda por usuario
|   |
│   ├── db/      
|   |   └── database_connector.py   # Conexión a base de datos
|   |
│   ├── routers/
│   │   ├── auth.py     # Rutas especificas para Login
│   │   └── main.py  #   Llamado de rutas para el sistema
│   │
│   ├── static/
|   |   |
│   │   ├── css/    # Estilos y animaciones
|   |   |   └──all.min.css      # CDN descargado para Tailwind CSS
|   |   |
│   │   ├── img/    # Imagenes y logos
|   |   |
│   │   ├── js/
|   |   |   └── alpine-collapse.min.js      # CDN descargado para animaciones Alpine.js
|   |   |   └── alpine.min.js   # CDN descargado para Alpine.js
|   |   |   └── upload_xlsx.js      # Lógica Js para obtener .xlsx
|   |   |   └── user_mark_day_records.js    # Lógica para edición de datos en funcionarios
|   |   | 
│   │   └── webfonts/  # Iconografia (font Awesome)
│   │
│   ├── templates/      # Vistas dinámicas HTML (Jinja2)
│   │   ├── admin/      # Secciones de Administrador
│   │   ├── auth/   # Login
│   │   ├── base/   # Plantilla padre (Jinja2)
│   │   ├── components/     # Plantillas reutilizables
│   │   └── users/
│   │       └── audit   # Plantillas principales
|   |           
│   ├── utils/      # Motores técnicos y auxiliares
│   │   ├── decorator.py    # Restricción de acceso por roles
│   │   ├── file_manager.py     # Funciones para manejo de archivos
│   │   └── register_engine.py      # Motor de datos principal
│   │
│   ├── app.py      # Inicialización de la app y definición de logs
│   └── run.py      # Punto de entrada para Dockerfile
|
├── Dockerfile     # Configuración de contenedor Flask app
└── requirements.txt    # Listado de dependencias y librerías de Python necesarias

.dockerignore    # Archivos y directorios a excluir al construir la imagen de Docker
.gitignore    # Archivos y directorios que Git debe ignorar en el control de versiones
db-sistema.sql    # Script SQL para la creación e inicialización de la base de datos
docker-compose.yml    # # Config. para levantar los servicios (base de datos y  app)
README.md    # Documentación principal del proyecto (este archivo)

```

> [!IMPORTANT]
> Algunos archivos no son mencionados ya que son solo maquetaciones de funcionalidades para escalabilidad futura.

> [!NOTE]
> Se usó Tailwind CSS y Alpine.js con descarga del CDN oficial, se requiere la compilación e instalación de ambos mediante npm para usar en producción.

---

### Descripción de componentes
 * **[controllers/](./sistema/app/controllers/):** Coordina la interacción entre el motor de ML, el sistema de archivos y la base de datos. Aquí se aloja la inteligencia operativa y la validación de registros.
 * **[routers/](./sistema/app/routers/):** Capa intermedia que define los accesos. **[auth.py](./sistema/app/routers/auth.py)** gestiona la seguridad, mientras **[main.py](./sistema/app/routers/main.py)** maneja la operativa diaria.
 * **[utils/](./sistema/app/utils/):** Contiene el código especializado como **[register_engine.py](./sistema/app/utils/register_engine.py)** (procesamiento de marcas) y el gestor de archivos **[file_manager.py](./sistema/app/utils/file_manager.py)**.
 * **[templates/](./sistema/app/templates/):** Utiliza un enfoque modular con layouts base y componentes reutilizables para optimizar la interfaz de usuario.

## Arquitectura de datos (ETL)
El sistema implementa un flujo ETL (Extract, Transform, Load) para convertir datos crudos en información procesada y automatizada.

### Flujo de datos
 1. **Extracción:** Lectura de archivos Excel (.xlsx) provenientes de dispositivos biométricos.
 2. **Transformación:** Limpieza de duplicados, normalización de formatos y validación lógica.
 3. **Carga:** Almacenamiento eficiente en formato columnar Parquet.

### DataFrames en memoria
| Estructura | Propósito | Salida |
|---|---|---|
| **df_principal** | Registro base de marcaciones. | .parquet |
| **df_resumen** | Análisis mensual y visualización de tendencias. | .parquet |
| **df_diario** | Métricas diarias de cumplimiento y atrasos. | .parquet |

## Motor de machine learning
El núcleo analítico utiliza un modelo de K-Means adaptativo para interpretar patrones de asistencia de forma autónoma.
 - **Lógica:** Determinación dinámica del valor K (número de marcas esperadas) según el comportamiento histórico del funcionario.
 - **Clasificación:** Clasificación automática de eventos en categorías: Entrada, Salida y Recesos.
 - **Regla crítica:** La intervención humana **(marcacionReal)** tiene prioridad absoluta sobre la predicción del modelo **(marcacionCluster)** para garantizar validez legal.



## Infraestructura y despliegue (Docker)

### Orquestación
Uso de **docker-compose** para orquestar los servicios:

| Contenedor | Propósito |
|---|---|
| **mysql_sistema_gestion** | Servidor de base de datos MySQL (v8.0.36) que centraliza y almacena de forma persistente la información del sistema. |
| **sistema_gestion_app** | Aplicación backend en Flask que maneja la lógica de negocio, el enrutamiento y el procesamiento de documentos. |

---

### Configuraciones clave del entorno (docker-compose.yml):
| Característica | Configuración / Variable | Descripción técnica |
|---|---|---|
| **Mapeo de puertos (BD)** | `3307:3306`| Se usa el puerto 3307 en la máquina local para conectar herramientas externas (ej. MySQL Workbench), evitando conflictos con instalaciones locales. Internamente, el contenedor usa el 3306. |
| **Mapeo de puertos (app)** | `5000:5000` | Conecta el puerto 5000 del entorno local directamente al puerto 5000 del contenedor web de Flask |
| **Modo debug (desarrollo)** | `FLASK_DEBUG=1` `FLASK_ENV=development` | Habilita la depuración de Flask y el "hot-reload", reflejando los cambios de código al instante sin reconstruir el contenedor. |
| **Zona horaria** | `TZ=America/Guayaquil` | Asegura que transacciones, registros de BD y logs se sincronicen con la hora local de Ecuador. |
| **Conexión interna** | `DB_HOST=db-sistema` | Flask resuelve la IP de la base de datos a través de la red interna usando el nombre del servicio. |
| **Persistencia de datos** | `./vol-data` `./vol-app` | Volúmenes que evitan la pérdida de la base de datos y archivos estáticos de la aplicación si el contenedor se destruye. |
| **Inicialización SQL** | `./db-sistema.sql` | Montado en `/docker-entrypoint-initdb.d/`, ejecuta el script de creación la primera vez que se levanta el contenedor de MySQL. |
| **Sincronización de Código** | `./sistema:/app/sistema` | Mapea el código fuente local dentro del contenedor para facilitar el desarrollo en tiempo real. |

---

### Construcción de la imagen Web:
El entorno de la aplicación backend se construye bajo las siguientes directrices en el Dockerfile:

| Componente | Directiva / Configuración | Propósito |
|---|---|---|
| **Imagen base** | `python:3.11-slim-bookworm` | Variante (basada en Debian) que reduce el peso de la imagen y agiliza los despliegues. |
| **Optimización de paquetes** | `pip install --no-cache-dir` | Instala las dependencias de Python sin almacenar la caché de descargas, manteniendo el contenedor liviano. |
| **Documentación de red** | `EXPOSE 5000` | Indica explícitamente el puerto por el cual el proceso web escuchará peticiones. |
| **Comando de ejecución (CMD)** | `--host=0.0.0.0 --debug` | Instruye a Flask a aceptar conexiones desde cualquier interfaz externa (fundamental en Docker) y refuerza el modo depuración en el arranque. |

---

>[!IMPORTANT]
> La escalabilidad del proyecto para ser alojado en un servidor Linux requiere de revisión y ajustes en el archivo **[docker-compose.yml](./docker-compose.yml)** o **[Dockerfile](./sistema/Dockerfile)** (en caso de ser necesario), para evitar problemas de ejecución en dichos entornos. 

>[!NOTE]
> Algunos ajustes y la ejecución de instalación de librerías dentro del archivo **[Dockerfile](./sistema/Dockerfile)** se omitieron por ser funcionalidades de escalabilidad. Los ajustes con credenciales de base de datos dentro del archivo **[docker-compose.yml](./docker-compose.yml)** se deben manejar de manera segura dentro del entorno. Las credenciales generadas otorgan privilegios de creación y manipulación dentro de la base de datos MySQL; estos deben ser ajustados según los requerimientos del proyecto y modificados en la estructura del archivo **[db-sistema.sql](./db-sistema.sql)** siguiendo protocolos estrictos de seguridad. Para este caso particular de desarrollo, se establecieron claves genéricas de acceso para el archivo de conexión de la base de datos ubicado en **[database_connector.py](./sistema/app/db/database_connector.py)**. Finalmente, el sistema está estructurado para escalar fácilmente e integrar **SQLAlchemy**, una potente librería de Python especializada en la comunicación y gestión de bases de datos mediante un ORM (Mapeo Objeto-Relacional), lo que optimizaría la ejecución de consultas complejas.

---

### Volúmenes
Los volúmenes almacenan la información persistente de la base de datos **(vol-data)** y la información persistente de la app Flask **(vol-app)**. Estos directorios dentro de Docker funcionan como volúmenes externos para guardar la información subida o editada en rutas específicas de directorios para el caso de la app.

 * **vol-app:** Persistencia de archivos cargados (uploads), registros de eventos (logs) y archivos de datos Parquet.
 * **vol-data:** Persistencia de la base de datos MySQL.

>[!NOTE]
> El volumen de la base de datos MySQL y de la app Flask se generan con la configuración de Docker compose en la raiz del proyecto. Esta configuración puede ser escalada para guardar la persistencia en rutas definidas por la configuración del servidor de alojamiento dentro de almacenamientos definidos por el analista de TI.

---

### Gestión de contenedores (Comandos Docker Compose)

Para administrar el ciclo de vida de la aplicación, utilizar los siguientes comandos desde la consola (CMD/Terminal), asegurando la ejecución de los mismos en el **directorio raíz del proyecto** (`/sistema-gestion`).

> [!IMPORTANT]
> Para la ejecución del proyecto en Windows, se requiere tener instalado y en ejecución **Docker Desktop**.No es necesario instalar las dependencias de Python localmente (en caso de hacerlo, usar un entorno virtual `env` en la raíz del proyecto `/sistema-gestion`), tampoco es necesario importar manualmente el archivo `db-sistema.sql`. La configuración de `docker-compose.yml` y `Dockerfile` automatiza la instalación de librerías y la inicialización de la base de datos durante la creación de los contenedores (`mysql_sistema_gestion`y `sistema_gestion_app` ).

---

**Iniciar el sistema (con reconstrucción):**

Levanta los servicios en segundo plano (`-d`) y fuerza la construcción de la imagen (`--build`). Se debe usar para el **primer arranque** o cuando hay cambios significativos.

```
docker compose up -d --build
```

>[!NOTE]
> Para levantar los contenedores que ya están construidos se debe usar `docker compose up -d`

---

**Detener el sistema:**

Detiene los contenedores en ejecución sin eliminar la red interna ni los volúmenes de datos.

```
docker compose down
```
---

**Reconstruir la imagen de la aplicación:**

Si el archivo **[requirements.txt](./sistema/requirements.txt)** es modificado (agregar o quitar librerías de Python) o se modifica el **[Dockerfile](./sistema/Dockerfile)**, se debe reconstruir la imagen del sistema para que los cambios surtan efecto.

```
docker compose build flask-app
```

---

**Detener y eliminar TODO (Contenedores y Volúmenes):**
> [!CAUTION]
> Uso en Desarrollo: El siguiente comando detiene los contenedores y elimina todos los volúmenes de datos asociados (`-v`), incluyendo la base de datos MySQL y los archivos estáticos guardados. Solo úsar si se necesita restablecer completamente el entorno de desarrollo y la base de datos a su estado inicial (el script **[db-sistema.sql](./db-sistema.sql)** volverá a ejecutarse en el próximo `up`).

```
docker compose down -v
```

---

## Base de datos MYSQL
El uso de MySQL es exclusivo para el manejo de autenticación, roles y usuarios dentro del sistema. La base de datos usada se descarga directamente en un contenedor aparte con la versión **mysql:8.0.36** definida en la configuración del **[docker-compose.yml](./docker-compose.yml)**.

El esquema de datos inicial al levantar el contenedor solo contiene un usuario Administrador definido con credenciales genéricas que deben ser cambiadas al momento del ingreso al sistema. La credencial de acceso al sistema del usuario **Admin Admin** está definida por la contraseña **Defaut1**; al momento del primer ingreso, el sistema pedirá el cambio de clave a una contraseña más segura antes de permitir operar en el sistema.

La estructura de la base de datos está definida dentro del archivo **[db-sistema.sql](./db-sistema.sql)**. Este archivo contiene la creación del esquema principal con las tablas principales y maestras que conforman el núcleo de la base de datos.

| Estructura | Propósito |
|---|---|
| **usuarios** | **Tabla principal:** Centraliza la información del personal, incluyendo datos personales (nombres, cédula), credenciales de seguridad (contraseñas encriptadas, requerimiento de cambio de clave) y estado de actividad. Actúa como el eje del sistema al vincular a cada usuario con su respectivo departamento y nivel de acceso. |
| **departamentos** | **Tabla maestra:** Contiene el catálogo de las distintas áreas o departamentos de la organización. Permite clasificar y organizar a los usuarios según el lugar donde operan. |
| **roles_sistema** | **Tabla maestra:** Define los diferentes niveles de privilegios (ej. administrador, empleado, etc.). Determina los permisos de cada usuario y qué funcionalidades o módulos del sistema puede utilizar. |

---

>[!IMPORTANT]
> El archivo `db-sistema.sql` contiene la creación de 2 esquemas dentro de la misma base de datos y la creación de otras tablas que no se mencionan en este documento. Estas tablas y el segundo esquema son funcionalidades de construcción esquematizadas para escalabilidad futura y aún no son relevantes para el proyecto, ya que están en proceso de desarrollo (build); por lo tanto, no se deben considerar dentro de esta versión base del sistema.


## Stack tecnológico
El sistema hace uso de diversas herramientas y tecnologías modernas distribuidas en diferentes capas, asegurando rendimiento, escalabilidad y un desarrollo ágil:

* **Backend y core:**
  * **Python:** Lenguaje principal de programación utilizado para toda la lógica de negocio.
  * **Flask:** Framework web ligero utilizado para el enrutamiento (routers), controladores y despliegue del servidor backend.

* **Procesamiento de datos e inteligencia artificial (ETL & ML):**
  * **Pandas:** Utilizado para la manipulación, limpieza y estructuración de datos en memoria (DataFrames) durante el flujo ETL.
  * **Scikit-learn (K-Means):** Librería utilizada para el motor de aprendizaje automático no supervisado, permitiendo clasificar y predecir los patrones de asistencia.
  * **Apache Parquet:** Sistema de persistencia columnar de alto rendimiento empleado para almacenar y consultar de manera eficiente los grandes volúmenes de registros biométricos procesados.

* **Base de datos:**
  * **MySQL (8.0.36):** Base de datos relacional dedicada de manera exclusiva a la gestión de accesos, roles, autenticación y almacenamiento de usuarios del sistema.

* **UX/UI:**
  * **HTML5 / Jinja2:** Motor de plantillas dinámicas integrado con Flask para la renderización de vistas (templates/).
  * **JavaScript (Vanilla & Fetch API):** Utilizado intensivamente en el frontend para la manipulación dinámica del DOM y el manejo de la lógica asíncrona. Se emplea el formato **JSON** como estándar de transporte de datos entre el cliente y el backend (Flask), permitiendo actualizar modales interactivos y mostrar cálculos dinámicos (como tiempos de atraso) en tiempo real sin recargar la página.
  * **Tailwind CSS:** Framework de CSS (basado en utilidades) empleado para el diseño y la maquetación de la interfaz.
  * **Alpine.js:** Framework ligero de JavaScript utilizado para manejar la interactividad del lado del cliente, componentes desplegables y animaciones de la UI.
  * **Font Awesome:** Librería de iconografía para la interfaz (webfonts).

* **Infraestructura y DevOps:**
  * **Docker:** Utilizado para la contenerización y aislamiento de los entornos de la aplicación.
  * **Docker Compose:** Herramienta de orquestación para levantar y conectar simultáneamente los servicios del sistema (App Flask, BD MySQL) junto con sus respectivos volúmenes de persistencia.

## Tecnologías utilizadas

A continuación se detallan las principales tecnologías, frameworks y herramientas empleadas para el desarrollo y despliegue del sistema:

<div align="center">

**Core & Backend**<br>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />

<br><br>**Procesamiento de Datos & Machine Learning**<br>
<img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
<img src="https://img.shields.io/badge/scikit_learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="Scikit-Learn" />
<img src="https://img.shields.io/badge/Apache_Parquet-E35A16?style=for-the-badge&logo=apache&logoColor=white" alt="Parquet" />

<br><br>**Frontend & UI**<br>
<img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
<img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript" />
<img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
<img src="https://img.shields.io/badge/Alpine.js-8BC0D0?style=for-the-badge&logo=alpine.js&logoColor=white" alt="Alpine.js" />

<br><br>**Infraestructura & Base de Datos**<br>
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
<img src="https://img.shields.io/badge/MySQL_8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL" />

</div>

## Colaboradores

Contribuidores al desarrollo y optimización del sistema realizado aportes al repositorio:

<div align="center">
  <img src="https://img.shields.io/github/last-commit/JoFNAr/sistema-gestion?style=flat-square&color=blue" alt="Último Commit" />
  <img src="https://img.shields.io/github/commit-activity/m/JoFNAr/sistema-gestion?style=flat-square&color=success" alt="Actividad de Commits" />
  <img src="https://img.shields.io/github/contributors/JoFNAr/sistema-gestion?style=flat-square&color=orange" alt="Contribuidores" />
</div>

<div align="center">
  <a href="https://github.com/JoFNAr/sistema-gestion/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=JoFNAr/sistema-gestion" alt="Mosaico de Colaboradores" />
  </a>
</div>
