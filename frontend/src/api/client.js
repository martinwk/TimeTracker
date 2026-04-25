// Dit bestand configureert axios (de HTTP client)

import axios from 'axios'

// Maak een axios "instance" met Django als baseURL
const client = axios.create({
  baseURL: 'http://localhost:8000/api',  // ← Django runs op 8000
  headers: {
    'Content-Type': 'application/json',
  },
})

// Export zodat andere bestanden het kunnen gebruiken
export default client