const mysql = require('mysql2');

// Create a connection pool
const pool = mysql.createPool({
  host: 'localhost',
  user: 'aiiovdft_bees',  
  password: 'FadiFadi2020',  
  database: 'aiiovdft_bees', 
  port: 3306,  
  connectionLimit: 10 
});

// Example query using the pool
const query = 'SELECT * FROM sensor_data';

pool.query(query, (err, results) => {
  if (err) {
    console.error('Error executing query:', err.message);
  } else {
    console.log('Query result:', results); 
  }
});

// Export the pool for use in other files
module.exports = pool;
