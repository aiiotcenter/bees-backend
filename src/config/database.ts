import mysql, { Pool, PoolOptions } from 'mysql2';

// Create a connection pool
const poolOptions: PoolOptions = {
  host: 'localhost',
  user: 'aiiovdft_bees',
  password: 'FadiFadi2020',
  database: 'aiiovdft_bees',
  port: 3306,
  connectionLimit: 10,
};

const pool: Pool = mysql.createPool(poolOptions);

// Test the connection
pool.getConnection((err, connection) => {
  if (err) {
    console.error('Database connection failed:', err.message);
  } else {
    console.log('Database connected successfully.');
    connection.release(); // Release the connection back to the pool
  }
});

export default pool.promise(); // Export the promise-based pool
