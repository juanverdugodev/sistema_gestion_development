-- Crear base de datos
CREATE DATABASE IF NOT EXISTS `sistema_gestion_db`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

use sistema_gestion_db;

-- Crear el usuario de app
create user 'app_user'@'%' identified by 'App@p4ssw0rd26';
grant all privileges on sistema_gestion_db.* to 'app_user'@'%';
flush privileges;

-- 1.. Tablas maestras (independientes)
create table departamentos (
	id_departamento int unsigned auto_increment,
    departamento varchar(100) not null,
    primary key (id_departamento),
    unique key uk_departamento (departamento)
) engine=InnoDB;

create table roles_sistema (
	id_rol int unsigned auto_increment,
    rol_privilegio varchar(100) not null,
    
    primary key (id_rol),
    unique key uk_rol (rol_privilegio)
) engine=InnoDB;

create table registros_meses_sistema (
	id_meses int unsigned auto_increment,
    meses_sistema varchar(50) not null,
    anio INT UNSIGNED NOT NULL,
    
    primary key (id_meses),
    unique key uk_mes_anio (meses_sistema, anio) -- llave única compuesta
) engine=InnoDB;

create table tipos_marcacion (
	id_tipo int unsigned auto_increment,
    codigo varchar(50) not null,
    
    primary key (id_tipo),
    unique key uk_codigo_tipo (codigo)
) engine=InnoDB;

create table estados_revision (
	id_estado int unsigned auto_increment,
    tipo varchar(50) not null,
    
    primary key (id_estado),
    unique key uk_tipo_estado (tipo)
) engine=InnoDB;

-- 2.. Tabla de usuarios (Main)
create table usuarios (
	id_usuario int unsigned auto_increment,
    nombres varchar(100) not null,
    apellidos varchar(100) not null,
    cedula varchar(10) null, -- Permite NULL para manejar N/A del CSV
    password_hash varchar(255) not null,    
    id_departamento int unsigned not null,
    id_rol int unsigned not null,
	change_password boolean not null default true,
    activo boolean not null default true,
    creado_en timestamp not null default current_timestamp,
	actualizado_en timestamp null on update current_timestamp,
    
    primary key (id_usuario),
    unique key uk_cedula (cedula),
    index idx_departamento (id_departamento),
    index idx_rol (id_rol),
    index idx_usuario_activo (activo),
    
    constraint fk_usuario_departamento
		foreign key (id_departamento) references departamentos (id_departamento)
        on delete restrict,
	constraint fk_usuario_rol
        foreign key (id_rol) references roles_sistema (id_rol)
        on delete restrict
) engine=InnoDB;

-- 3.. Tablas operativas (dependientes)
create table registro_dias (
	id_dias int unsigned auto_increment,
    id_meses int unsigned not null,
    id_usuario int unsigned not null,
    fecha_registro date not null,
    motivo_justificacion varchar(150) null,
    detalle_justificacion text null,
    
    primary key (id_dias),
    unique key uk_usuario_fecha (id_usuario, fecha_registro), -- Evita duplicar el mismo día para un usuario
    index idx_meses (id_meses),
    index idx_fecha_registro (fecha_registro),
    
    constraint fk_dias_meses
		foreign key (id_meses) references registros_meses_sistema (id_meses)
        on delete restrict,
	constraint fk_dias_usuario
		foreign key (id_usuario) references usuarios (id_usuario)
        on delete restrict
) engine=InnoDB;

create table registro_horas (
	id_horas int unsigned auto_increment,
	id_dias int unsigned not null,
    id_tipo_marcacion int unsigned not null,
    id_estado_revision int unsigned not null,
    origen enum('csv','manual','ajuste','omr') not null,
    hora time not null,
    creado_en timestamp not null default current_timestamp,
    actualizado_en timestamp null on update current_timestamp,
    
    primary key (id_horas),
    index idx_opt_busqueda (id_dias,hora),
    index idx_origen_marcacion (origen),
    
    constraint fk_horas_dias
		foreign key (id_dias) references registro_dias(id_dias)
        on delete restrict,-- Bloquea el borrado del día si hay hora
	constraint fk_horas_tipo
		foreign key (id_tipo_marcacion) references tipos_marcacion (id_tipo)
        on delete restrict,
	constraint fk_horas_estado
		foreign key (id_estado_revision) references estados_revision(id_estado)
		on delete restrict
) engine=InnoDB;


-- 3. Insertar usuario inicial Admin
insert into departamentos (departamento) values ('Administrador de sistema');
insert into roles_sistema (rol_privilegio) values ('Administrador'), ('Usuario');

insert into usuarios (nombres, apellidos, cedula, password_hash,
id_departamento, id_rol, change_password, activo)
values ('Admin', 'Admin', '0123456789', 'pbkdf2:sha256:600000$CPmPAzVNuwdRqKw9$c4b3be9bac58493dc7b7e057710e889a041c33074e3e2c29f52567715eb8617f', 1, 1, true, true);

-- 4. Insertar catálogos básicos
insert into estados_revision (tipo) values ('Pendiente'), ('Valido'), ('Anormal'), ('Descartado'), ('Justificada');

insert into tipos_marcacion (codigo) 
values ('Entrada principal'), ('Salida intermedia (Descanso)'), ('Entrada intermedia (Retorno)'),
('Salida principal'), ('Entrada justificada'), ('Salida justificada');






-- Creación del nuevo esquema para los registros
-- Crear la base de datos sistema_gestion_registros_db
create database if not exists`sistema_gestion_registros_db`
character set utf8mb4
collate utf8mb4_unicode_ci;

-- Cambiar al nuevo esquema para crear las tablas
use sistema_gestion_registros_db;

-- Dar privilegios al usuario existente 'app_user' sobre este nuevo esquema
grant all privileges on sistema_gestion_registros_db.* to 'app_user'@'%';

flush privileges;

-- Creación de Tablas del Nuevo Esquema

-- 1. Tabla de Departamentos (Catálogo)
create table departamentos (
    id_departamento int auto_increment,
    nombre_departamento varchar(100) not null,
    primary key (id_departamento),
    unique key uk_nombre_departamento (nombre_departamento)
) engine=InnoDB;

-- 2. Tabla de Banderas de Actividad (Catálogo de tipos de marcación)
create table banderas_actividad (
    id_bandera tinyint auto_increment,
    nombre_bandera varchar(50) not null,
    primary key (id_bandera),
    unique key uk_nombre_bandera (nombre_bandera)
) engine=InnoDB;

-- 3. Tabla de Estados de Registro
create table estados_registro (
    id_estado tinyint auto_increment,
    nombre_estado varchar(50) not null, -- Ej: Válido, Descartado, Actualizado
    primary key (id_estado),
    unique key uk_nombre_estado (nombre_estado)
) engine=InnoDB;

-- 4. Tabla de Funcionarios (Main)
create table funcionarios (
    id_funcionario int auto_increment,
    id_departamento int not null,
    nombres varchar(100) not null,
    apellidos varchar(100) not null,
    cedula varchar(10) null unique, 
    creado_en timestamp not null default current_timestamp,
    actualizado_en timestamp null on update current_timestamp,
    
    primary key (id_funcionario),
    index idx_departamento_func (id_departamento),
    
    constraint fk_func_departamento 
        foreign key (id_departamento) references departamentos(id_departamento) 
        on delete restrict
) engine=InnoDB;

-- 5. Tabla Central Transaccional: Registros de Actividad (Indexada y Auditada)
create table registros_actividad (
    id_registro int auto_increment,
    id_funcionario int not null,
    fecha_registro date not null,
    hora_registro time not null,
    id_bandera tinyint not null,
    id_estado tinyint not null default 1, -- Por defecto todo entra como estado 1 (Válido/Pendiente)
    
    -- Orígen de la marcación
    metodo_registro enum('FP', 'FACE', 'OMR', 'MANUAL') not null, 
    
    creado_en timestamp not null default current_timestamp,
    actualizado_en timestamp null on update current_timestamp,
    
    primary key (id_registro),
    index idx_funcionario_fecha (id_funcionario, fecha_registro),
    index idx_metodo (metodo_registro),
    index idx_estado (id_estado), -- Índice para filtrar rápidamente los "Descartados"
    
    constraint fk_reg_funcionario 
        foreign key (id_funcionario) references funcionarios(id_funcionario) 
        on delete restrict,
        
    constraint fk_reg_bandera 
        foreign key (id_bandera) references banderas_actividad(id_bandera) 
        on delete restrict,
        
    constraint fk_reg_estado
        foreign key (id_estado) references estados_registro(id_estado)
        on delete restrict
) engine=InnoDB;

-- Inserción de Catálogos Iniciales

INSERT INTO estados_registro (nombre_estado) VALUES 
('Válido'),       -- ID 1: Registro normal y funcional
('Descartado'),   -- ID 2: Registro anulado (no se muestra en reportes finales)
('Actualizado'),  -- ID 3: Registro que fue modificado manualmente por ajuste de RRHH
('Pendiente');    -- ID 4: Registro que requiere revisión o aprobación (Ej: Comisiones)


insert into banderas_actividad (nombre_bandera) values 
('Entrada'),           -- ID 1
('Salida Almuerzo'),   -- ID 2
('Regreso Almuerzo'),  -- ID 3
('Salida'),            -- ID 4
('Salida Comisión'),   -- ID 5
('Regreso Comisión');  -- ID 6


delimiter //

CREATE TRIGGER tr_asignar_estado_comision
BEFORE INSERT ON registros_actividad
FOR EACH ROW
BEGIN
    -- Si la bandera que se está insertando es 5 (Salida Comisión) o 6 (Regreso Comisión)
    IF NEW.id_bandera IN (5, 6) THEN
        -- Sobrescribimos cualquier estado por defecto o enviado y le asignamos 4 (Pendiente)
        SET NEW.id_estado = 4;
    END IF;
END; //

delimiter ;