# 💻 Sistema de Gestión

Aplicación desarrollada con **Flask** y **MySQL 8.0.36** ejecutado en **Docker**, diseñada para un entorno de desarrollo portable.

---

## 📑 Índice

- [🏗 Arquitectura del Proyecto](#-arquitectura-del-proyecto)
- [📦 Requisitos](#-requisitos)
- [🐳 Base de Datos MySQL en Docker](#-base-de-datos-mysql-en-docker)

---

## 🏗 Arquitectura del Proyecto

El sistema está compuesto por:
- **Aplicación Flask:** Ubicada en `/sistema`.
- **Contenedor MySQL:** Ejecutado en Docker.
- **Volumen Persistente:** Carpeta `/vol-data` para que los datos no se pierdan al apagar el contenedor.

> [!NOTE]
> Esta arquitectura permite bases de datos distintas entre computadoras con la misma estructura de datos.

---

## 📦 Requisitos

* **Docker Desktop** (en ejecución).
* **Terminal:** Windows (CMD).
* **Puerto 3307** libre en la máquina local.

---

## 🐳 Base de Datos MySQL en Docker

Los datos se almacenan localmente en la carpeta `/vol-data`. Para levantar el entorno, leer las instrucciones del archivo.

> [!IMPORTANT]
> Revisar el archivo [vol-data/README.md](./vol-data/README.md) para crear el contenedor con MySQL.