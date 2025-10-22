-- Eliminar usuario si existe
DROP USER IF EXISTS 'exporter'@'%';

-- Crear usuario con todos los privilegios necesarios
CREATE USER 'exporter'@'%' IDENTIFIED BY 'omj123';

-- Otorgar privilegios necesarios
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'%';
GRANT SUPER ON *.* TO 'exporter'@'%';

-- Actualizar privilegios
FLUSH PRIVILEGES;