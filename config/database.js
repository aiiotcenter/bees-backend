const mysql = require('mysql2');

// Create a connection pool
const pool = mysql.createPool({
  host: 'localhost',
  user: 'root',
  password: 'FadiFadi2020',  // Default password for MAMP MySQL
  database: 'aiiovdft_bees',  // Your database name
  port: 3306,  // Default port for MAMP MySQL
  connectionLimit: 10  // Limit on the number of connections in the pool
});

// Example query using the pool
const query = 'SELECT * FROM sensor_data';

pool.query(query, (err, results) => {
  if (err) {
    console.error('Error executing query:', err.message);  // Log query execution error
  } else {
    console.log('Query result:', results);  // Log the query results
  }
});

// Export the pool for use in other files
module.exports = pool;
