import { useState, useRef, useEffect } from 'react'
import { renderBreakingNews } from '../utils/canvasRenderer'
import './NewsGenerator.css'

// Helper function to get EST time
function getESTTime() {
  // Get current time in EST/EDT timezone (America/New_York)
  // Use Intl API to get EST time components and create a date object
  const now = new Date()
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
  const parts = formatter.formatToParts(now)
  const year = parseInt(parts.find(p => p.type === 'year').value)
  const month = parseInt(parts.find(p => p.type === 'month').value) - 1 // Month is 0-indexed
  const day = parseInt(parts.find(p => p.type === 'day').value)
  const hour = parseInt(parts.find(p => p.type === 'hour').value)
  const minute = parseInt(parts.find(p => p.type === 'minute').value)
  const second = parseInt(parts.find(p => p.type === 'second').value)
  
  // Create a date object with EST time values
  // Note: This creates a date in local timezone but with EST time values
  return new Date(year, month, day, hour, minute, second)
}

function NewsGenerator() {
  const [headline, setHeadline] = useState('')
  const [ticker, setTicker] = useState('')
  const [image, setImage] = useState(null)
  const imageSize = 'wide' // Always use wide rectangle
  const [imagePreview, setImagePreview] = useState(null)
  const [currentTime, setCurrentTime] = useState(getESTTime())
  const [imageUrl, setImageUrl] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const canvasRef = useRef(null)
  const dropZoneRef = useRef(null)

  const imageSizes = {
    wide: { width: 1920, height: 1080, label: 'Wide Rectangle' },
    square: { width: 1080, height: 1080, label: 'Square' },
    portrait: { width: 1080, height: 1350, label: 'Portrait' }
  }

  // Update time every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(getESTTime())
    }, 60000) // Update every minute

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (canvasRef.current && (headline || ticker || imagePreview)) {
      renderBreakingNews(
        canvasRef.current,
        imagePreview,
        headline,
        ticker,
        imageSizes[imageSize],
        currentTime
      )
    }
  }, [headline, ticker, imagePreview, imageSize, currentTime])

  const loadImageFromFile = (file) => {
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
      setImage(file)
      setImageUrl('') // Clear URL when file is loaded
    }
  }

  const loadImageFromUrl = async (url) => {
    try {
      // Validate URL
      new URL(url) // Throws if invalid
      
      // Try to load the image
      const img = new Image()
      img.crossOrigin = 'anonymous' // Handle CORS
      
      img.onload = () => {
        // Convert image to data URL
        const canvas = document.createElement('canvas')
        canvas.width = img.width
        canvas.height = img.height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0)
        
        try {
          const dataUrl = canvas.toDataURL('image/png')
          setImagePreview(dataUrl)
          setImage(null) // Clear file when URL is loaded
        } catch (error) {
          console.error('Error converting image:', error)
          alert('Unable to load image from URL. The image may be blocked by CORS policy.')
        }
      }
      
      img.onerror = () => {
        alert('Unable to load image from URL. Please check the URL and try again.')
      }
      
      img.src = url
    } catch (error) {
      alert('Please enter a valid image URL')
    }
  }

  const handleImageUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      loadImageFromFile(file)
    }
  }

  const handleUrlSubmit = (e) => {
    e.preventDefault()
    if (imageUrl.trim()) {
      loadImageFromUrl(imageUrl.trim())
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      loadImageFromFile(files[0])
    }
  }

  // Add paste event listener
  useEffect(() => {
    const handlePaste = (e) => {
      const items = e.clipboardData?.items
      if (!items) return

      for (let i = 0; i < items.length; i++) {
        const item = items[i]
        
        // Check for pasted image
        if (item.type.indexOf('image') !== -1) {
          const blob = item.getAsFile()
          if (blob) {
            const reader = new FileReader()
            reader.onloadend = () => {
              setImagePreview(reader.result)
            }
            reader.readAsDataURL(blob)
            setImage(blob)
            setImageUrl('')
            return
          }
        }
        
        // Check for pasted text (URL)
        if (item.type === 'text/plain') {
          item.getAsString((text) => {
            // Check if it looks like a URL
            if (text.trim().match(/^https?:\/\/.+\.(jpg|jpeg|png|gif|webp|svg)/i)) {
              setImageUrl(text.trim())
              // Load image from URL
              const img = new Image()
              img.crossOrigin = 'anonymous'
              img.onload = () => {
                const canvas = document.createElement('canvas')
                canvas.width = img.width
                canvas.height = img.height
                const ctx = canvas.getContext('2d')
                ctx.drawImage(img, 0, 0)
                try {
                  const dataUrl = canvas.toDataURL('image/png')
                  setImagePreview(dataUrl)
                  setImage(null)
                } catch (error) {
                  console.error('Error converting image:', error)
                  alert('Unable to load image from URL. The image may be blocked by CORS policy.')
                }
              }
              img.onerror = () => {
                alert('Unable to load image from URL. Please check the URL and try again.')
              }
              img.src = text.trim()
            }
          })
        }
      }
    }

    window.addEventListener('paste', handlePaste)
    return () => {
      window.removeEventListener('paste', handlePaste)
    }
  }, [])

  const handleDownload = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const link = document.createElement('a')
    link.download = 'breaking-news.png'
    link.href = canvas.toDataURL('image/png')
    link.click()
  }

  return (
    <div className="news-generator">
      <div className="generator-container">
        <div className="controls-panel">
          <div className="control-group">
            <label htmlFor="headline">Headline</label>
            <textarea
              id="headline"
              value={headline}
              onChange={(e) => {
                let newValue = e.target.value
                // Limit to 90 characters total (45 per line)
                if (newValue.length > 90) {
                  newValue = newValue.substring(0, 90)
                }
                
                // Ensure each line is max 45 characters
                const lines = newValue.split('\n')
                if (lines[0].length > 45) {
                  lines[0] = lines[0].substring(0, 45)
                }
                if (lines.length > 1 && lines[1].length > 45) {
                  lines[1] = lines[1].substring(0, 45)
                }
                // Limit to 2 lines max
                const finalValue = lines.slice(0, 2).join('\n')
                setHeadline(finalValue)
              }}
              placeholder="Enter your headline...&#10;Add a second line for subtitle (press Enter)"
              className="text-input textarea-input"
              rows={3}
              maxLength={90}
            />
            <div className="character-count">
              <small className="input-hint">
                First line is the main headline (bold, larger). Second line is subtitle (smaller).
              </small>
              <small className="char-counter">
                {headline.length}/90 characters (45 per line max)
              </small>
            </div>
          </div>

          <div className="control-group">
            <label htmlFor="ticker">Ticker</label>
            <input
              type="text"
              id="ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="Enter ticker text..."
              className="text-input"
            />
          </div>

          <div className="control-group">
            <label htmlFor="imageUpload">Your Image</label>
            <div 
              className={`image-upload ${isDragging ? 'dragging' : ''}`}
              ref={dropZoneRef}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                type="file"
                id="imageUpload"
                accept="image/*"
                onChange={handleImageUpload}
                className="file-input"
              />
              <label htmlFor="imageUpload" className="file-label">
                {image ? 'Change Image' : 'Choose Image'}
              </label>
              {image && (
                <span className="file-name">{image.name}</span>
              )}
              <div className="upload-divider">
                <span>or</span>
              </div>
              <form onSubmit={handleUrlSubmit} className="url-input-form">
                <input
                  type="text"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  placeholder="Paste image URL here..."
                  className="url-input"
                />
                <button type="submit" className="url-submit-button">
                  Load
                </button>
              </form>
              <small className="upload-hint">
                Drag & drop an image, paste from clipboard, or paste a URL
              </small>
            </div>
          </div>

          <button
            onClick={handleDownload}
            className="download-button"
            disabled={!headline && !ticker && !imagePreview}
          >
            Download your image
          </button>
        </div>

        <div className="preview-panel">
          <div className="canvas-container">
            <canvas
              ref={canvasRef}
              width={imageSizes[imageSize].width}
              height={imageSizes[imageSize].height}
              className="preview-canvas"
            />
            {!headline && !ticker && !imagePreview && (
              <div className="canvas-placeholder">
                <p>Your browser does not support HTML5 Canvas.</p>
                <p>Add a headline, ticker, or image to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default NewsGenerator
