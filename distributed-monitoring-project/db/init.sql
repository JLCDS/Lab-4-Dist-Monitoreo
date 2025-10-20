-- Crear base de datos y tabla de libros
CREATE DATABASE IF NOT EXISTS books_db;
USE books_db;

CREATE TABLE IF NOT EXISTS books (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  author VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- Registros iniciales
INSERT INTO books (title, author) VALUES
("1984", "George Orwell"),
("Cien años de soledad", "Gabriel García Márquez");
