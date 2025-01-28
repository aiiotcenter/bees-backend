"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const mysql2_1 = __importDefault(require("mysql2"));
// Create a connection pool
const poolOptions = {
    host: 'localhost',
    user: 'aiiovdft_bees',
    password: 'FadiFadi2020',
    database: 'aiiovdft_bees',
    port: 3306,
    connectionLimit: 10,
};
const pool = mysql2_1.default.createPool(poolOptions);
// Test the connection
pool.getConnection((err, connection) => {
    if (err) {
        console.error('Database connection failed:', err.message);
    }
    else {
        console.log('Database connected successfully.');
        connection.release(); // Release the connection back to the pool
    }
});
exports.default = pool.promise(); // Export the promise-based pool
