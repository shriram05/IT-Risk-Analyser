import axios from 'axios'

const BASE = '/api'

export async function fetchGraph() {
  const { data } = await axios.get(`${BASE}/graph`)
  return data
}

export async function streamAnalysis(alertText, onEvent) {
  const response = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_text: alertText }),
  })

  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6))
          onEvent(event)
        } catch {
          // skip malformed lines
        }
      }
    }
  }
}
