// Dit bestand bevat functies om projects op te halen, de django API van de
// projects app aan te roepen. Deze functies worden gebruikt in App.vue

import client from './client'

// Functie: Haal alle projecten op
export async function getProjects() {
  try {
    // GET request naar /api/projects/
    const response = await client.get('/projects/')

    // Response kan nested data hebben (results: [...])
    // Dus: return data.results OR data (fallback)
    return response.data.results || response.data
  } catch (error) {
    console.error('Error fetching projects:', error)
    throw error  // Gooi error door zodat App.vue het kan opvangen
  }
}

// Functie: Maak nieuw project
export async function createProject(name, color) {
  try {
    const response = await client.post('/projects/', {
      name: name,
      color: color,
      is_active: true,
    })
    return response.data
  } catch (error) {
    console.error('Error creating project:', error)
    throw error
  }
}