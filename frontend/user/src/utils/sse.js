export async function chatStream(url, body, onChunk, onDone, onError) {
  const token = localStorage.getItem('token')
  try {
    const response = await fetch(`/api/v1${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      let errorMsg = `HTTP error: ${response.status}`
      try {
        const errorData = await response.json()
        if (errorData.detail) {
          errorMsg = errorData.detail
        } else if (errorData.message) {
          errorMsg = errorData.message
        }
      } catch {
        // ignore JSON parse error
      }
      throw new Error(errorMsg)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (!data) continue
          try {
            const parsed = JSON.parse(data)
            if (parsed.done) {
              onDone && onDone(parsed)
            } else if (parsed.error) {
              onError && onError(parsed.error)
            } else if (parsed.content) {
              onChunk && onChunk(parsed.content)
            }
          } catch {
            // skip invalid JSON
          }
        }
      }
    }
  } catch (e) {
    onError && onError(e.message)
  }
}
