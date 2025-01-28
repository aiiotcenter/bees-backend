import mysql, { Pool, PoolOptions } from 'mysql2';

// Define the pool options
const poolOptions: PoolOptions = {
  host: 'localhost',
  user: 'aiiovdft_bees',
  password: 'FadiFadi2020',
  database: 'aiiovdft_bees',
  port: 3306,
  connectionLimit: 10, // The maximum number of connections in the pool
};

// Create the MySQL pool
const pool: Pool = mysql.createPool(poolOptions);

// Export a promise-based pool for better async/await handling
const promisePool = pool.promise();

// Test the connection to the database
async function testConnection() {
  try {
    const [rows] = await promisePool.query('SELECT 1 + 1 AS solution');
    console.log('Database connected successfully:', rows);
  } catch (error: unknown) {
    // Log the entire error object for better diagnostics
    console.error('Error connecting to the database:', error);

    // If the error is an instance of Error, log the message
    if (error instanceof Error) {
      console.error('Error message:', error.message);
    } else {
      console.error('Unknown error type');
    }
  }
}


// Call the test function
testConnection();

// Export the promise pool for use in other parts of your application
export default promisePool;
