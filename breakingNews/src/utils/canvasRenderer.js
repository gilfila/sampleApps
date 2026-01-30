/**
 * Renders a breaking news style image on a canvas
 * @param {HTMLCanvasElement} canvas - The canvas element to draw on
 * @param {string|null} backgroundImage - Data URL of the background image
 * @param {string} headline - The headline text
 * @param {string} ticker - The ticker text
 * @param {Object} size - Size object with width and height
 * @param {Date} currentTime - Current time in EST timezone
 */
export function renderBreakingNews(canvas, backgroundImage, headline, ticker, size, currentTime = null) {
  const ctx = canvas.getContext('2d')
  
  // Set canvas dimensions
  canvas.width = size.width
  canvas.height = size.height
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // Draw background
  if (backgroundImage) {
    const img = new Image()
    img.onload = () => {
      drawComplete(ctx, img, headline, ticker, canvas.width, canvas.height, currentTime)
    }
    img.src = backgroundImage
  } else {
    // Default gradient background if no image
    drawGradientBackground(ctx, canvas.width, canvas.height)
    drawComplete(ctx, null, headline, ticker, canvas.width, canvas.height, currentTime)
  }
}

function drawComplete(ctx, bgImage, headline, ticker, width, height, currentTime = null) {
  // Clear and redraw background
  ctx.clearRect(0, 0, width, height)
  
  if (bgImage) {
    // Calculate scaling to cover the canvas while maintaining aspect ratio
    const imgAspect = bgImage.width / bgImage.height
    const canvasAspect = width / height
    
    let drawWidth, drawHeight, drawX, drawY
    
    if (imgAspect > canvasAspect) {
      // Image is wider - fit to height
      drawHeight = height
      drawWidth = height * imgAspect
      drawX = (width - drawWidth) / 2
      drawY = 0
    } else {
      // Image is taller - fit to width
      drawWidth = width
      drawHeight = width / imgAspect
      drawX = 0
      drawY = (height - drawHeight) / 2
    }
    
    // Draw image without darkening overlay
    ctx.drawImage(bgImage, drawX, drawY, drawWidth, drawHeight)
  } else {
    drawGradientBackground(ctx, width, height)
  }
  
  // Draw LIVE badge at top-left
  drawLiveBadge(ctx, width, height)
  
  // Draw "BREAKING NEWS" banner at bottom (above headline box)
  // Pass headline so banner can adjust height to match gray box
  drawBreakingBanner(ctx, width, height, headline)
  
  // Draw headline in gray box
  if (headline) {
    drawHeadline(ctx, headline, width, height)
  }
  
  // Draw ticker at bottom with time
  if (ticker) {
    drawTicker(ctx, ticker, width, height, currentTime)
  }
}

function drawGradientBackground(ctx, width, height) {
  const gradient = ctx.createLinearGradient(0, 0, width, height)
  gradient.addColorStop(0, '#1a1a2e')
  gradient.addColorStop(1, '#16213e')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, height)
}

function drawLiveBadge(ctx, width, height) {
  const badgeWidth = Math.floor(width * 0.08)
  const badgeHeight = Math.floor(badgeWidth * 0.4)
  const padding = Math.floor(width * 0.02)
  
  // Red background
  ctx.fillStyle = '#dc2626'
  ctx.fillRect(padding, padding, badgeWidth, badgeHeight)
  
  // White text
  ctx.fillStyle = '#ffffff'
  ctx.font = `bold ${Math.floor(badgeHeight * 0.7)}px Arial, sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  
  ctx.fillText('LIVE', padding + badgeWidth / 2, padding + badgeHeight / 2)
}

function drawBreakingBanner(ctx, width, height, headline = '') {
  const tickerHeight = Math.floor(height * 0.08)
  const baseHeadlineBoxHeight = Math.floor(height * 0.12)
  const bannerHeight = Math.floor(height * 0.08)
  
  // Always use 2-line height for the gray box (same as in drawHeadline)
  const estimatedFontSize = Math.floor(width * 0.08) // Estimate for calculation
  const lineHeight = estimatedFontSize * 1.3 // Font size * 1.3 line height
  const lineSpacing = 0 // No spacing between lines
  
  // Always use 2-line height for consistency, then reduce by 10%
  const headlineBoxHeight = Math.floor((baseHeadlineBoxHeight + lineHeight + lineSpacing) * 0.9)
  
  // Banner is 30% width on the left side
  const bannerWidth = Math.floor(width * 0.3)
  
  // Combined height to extend behind headline box (dynamic)
  const combinedHeight = bannerHeight + headlineBoxHeight
  
  // Position at bottom, same y as headline box (will be behind it, rises with gray box)
  const bannerY = height - tickerHeight - headlineBoxHeight - bannerHeight
  
  // Red background - 30% width, left side, extended height
  ctx.fillStyle = '#dc2626'
  ctx.fillRect(0, bannerY, bannerWidth, combinedHeight)
  
  // White text with drop shadow - left aligned with padding
  ctx.fillStyle = '#ffffff'
  ctx.font = `bold ${Math.floor(bannerHeight * 0.6)}px Arial, sans-serif`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  
  // Add drop shadow
  ctx.shadowColor = 'rgba(0, 0, 0, 0.5)'
  ctx.shadowBlur = Math.floor(width * 0.01)
  ctx.shadowOffsetX = Math.floor(width * 0.003)
  ctx.shadowOffsetY = Math.floor(width * 0.003)
  
  // Left padding for text
  const textPadding = Math.floor(width * 0.02)
  ctx.fillText('BREAKING NEWS', textPadding, bannerY + bannerHeight / 2)
  
  // Reset shadow for other elements
  ctx.shadowColor = 'transparent'
  ctx.shadowBlur = 0
  ctx.shadowOffsetX = 0
  ctx.shadowOffsetY = 0
}

function drawHeadline(ctx, headline, width, height) {
  const tickerHeight = Math.floor(height * 0.08)
  const baseHeadlineBoxHeight = Math.floor(height * 0.12)
  const breakingBannerHeight = Math.floor(height * 0.08)
  
  // Always use 2-line height for the gray box (keep it consistent size)
  // Calculate headline box height - always sized for 2 lines, then shrink by 10%
  const estimatedFontSize = Math.floor(width * 0.08) // Estimate for calculation
  const lineHeight = estimatedFontSize * 1.3 // Font size * 1.3 line height
  const lineSpacing = 0 // No spacing between lines
  
  // Always use 2-line height for consistency, then reduce by 10%
  const headlineBoxHeight = Math.floor((baseHeadlineBoxHeight + lineHeight + lineSpacing) * 0.9)
  
  // Position breaking news banner and gray box together
  // The banner should rise up with the gray box
  const bannerY = height - tickerHeight - headlineBoxHeight - breakingBannerHeight
  const headlineBoxY = bannerY + breakingBannerHeight
  
  // Draw gray background box - 5% from left, 95% width, dynamic height
  const grayBoxX = Math.floor(width * 0.05)
  const grayBoxWidth = Math.floor(width * 0.95)
  ctx.fillStyle = '#e5e5e5'
  ctx.fillRect(grayBoxX, headlineBoxY, grayBoxWidth, headlineBoxHeight)
  
  if (!headline || headline.trim() === '') return
  
  // Enforce character limits: 90 total (45 per line), 45 per line
  let processedHeadline = headline.trim()
  if (processedHeadline.length > 90) {
    processedHeadline = processedHeadline.substring(0, 90)
  }
  
  // Split headline by newlines to support multi-line titles
  let headlineLines = processedHeadline.split('\n').filter(line => line.trim() !== '')
  if (headlineLines.length === 0) return
  
  // Enforce 45 character limit per line
  if (headlineLines[0].length > 45) {
    headlineLines[0] = headlineLines[0].substring(0, 45)
  }
  if (headlineLines.length > 1 && headlineLines[1].length > 45) {
    headlineLines[1] = headlineLines[1].substring(0, 45)
  }
  
  // Calculate available width (gray box width minus padding)
  const leftPadding = Math.floor(width * 0.015) // Small padding for readability
  const rightPadding = Math.floor(width * 0.02)
  const maxWidth = grayBoxWidth - leftPadding - rightPadding
  
  // Text X position starts at left edge of gray box + small padding
  const textX = grayBoxX + leftPadding
  
  // Main headline (first line)
  const mainHeadline = headlineLines[0].trim()
  
  // Start with maximum font size - calculate based on reference text
  // Use a 30-character reference text to fill the gray box
  const referenceText = "THIS IS AN IMPORTANT HEAD" // 30 characters
  const numLines = headlineLines.length
  
  // Find the font size that makes the reference text fill the width
  // Start with larger size since we have fewer characters (30 vs 50)
  let referenceFontSize = Math.floor(width * 0.12) // Start larger for 30 chars
  ctx.font = `${referenceFontSize}px "Oswald", Arial, sans-serif`
  let referenceMetrics = ctx.measureText(referenceText)
  
  // Adjust to make reference text fill the entire available width (100%)
  while (referenceMetrics.width < maxWidth && referenceFontSize < width * 0.20) {
    referenceFontSize += 1
    ctx.font = `${referenceFontSize}px "Oswald", Arial, sans-serif`
    referenceMetrics = ctx.measureText(referenceText)
  }
  // If it exceeds, back off one step to fit exactly
  while (referenceMetrics.width > maxWidth && referenceFontSize > 20) {
    referenceFontSize -= 1
    ctx.font = `${referenceFontSize}px "Oswald", Arial, sans-serif`
    referenceMetrics = ctx.measureText(referenceText)
  }
  
  // Use reference size as starting point
  // For single line, make it larger to visually fill the 2-line box height
  // For two lines, make first line larger than second line
  const baseMaxFontSize = numLines === 1 
    ? Math.floor(referenceFontSize * 1.6)  // Even larger for single line to fill 2-line box
    : Math.floor(referenceFontSize * 1.3)  // Larger first line for two-line titles
  let mainFontSize = baseMaxFontSize
  
  // Calculate optimal font size for actual headline - start large and reduce until it fits
  ctx.font = `${mainFontSize}px "Oswald", Arial, sans-serif`
  let mainMetrics = ctx.measureText(mainHeadline.toUpperCase())
  
  // Reduce font size if text is too wide - binary search for optimal size
  if (mainMetrics.width > maxWidth) {
    let minSize = 20
    let maxSize = mainFontSize
    
    // Binary search for the largest font size that fits
    while (maxSize - minSize > 1) {
      const testSize = Math.floor((minSize + maxSize) / 2)
      ctx.font = `${testSize}px "Oswald", Arial, sans-serif`
      const testMetrics = ctx.measureText(mainHeadline.toUpperCase())
      
      if (testMetrics.width <= maxWidth) {
        minSize = testSize
      } else {
        maxSize = testSize
      }
    }
    
    // Use the size that fits
    mainFontSize = minSize
    ctx.font = `${mainFontSize}px "Oswald", Arial, sans-serif`
    mainMetrics = ctx.measureText(mainHeadline.toUpperCase())
  }
  
  // Wrap main headline if still too long
  let mainLines = []
  if (mainMetrics.width > maxWidth) {
    const words = mainHeadline.toUpperCase().split(' ')
    let currentLine = words[0]
    
    for (let i = 1; i < words.length; i++) {
      const testLine = currentLine + ' ' + words[i]
      const testMetrics = ctx.measureText(testLine)
      
      if (testMetrics.width > maxWidth && currentLine.length > 0) {
        mainLines.push(currentLine)
        currentLine = words[i]
      } else {
        currentLine = testLine
      }
    }
    mainLines.push(currentLine)
  } else {
    mainLines = [mainHeadline.toUpperCase()]
  }
  
  // Subtitle (second line if present) - smaller than main headline
  let subtitleLines = []
  let subtitleFontSize = Math.floor(mainFontSize * 0.85) // Smaller than first line (85% of first line size)
  if (headlineLines.length > 1) {
    const subtitle = headlineLines[1].trim()
    
    // Test subtitle with current font size
    ctx.font = `${subtitleFontSize}px "Oswald", Arial, sans-serif`
    let subtitleMetrics = ctx.measureText(subtitle)
    
    // If subtitle doesn't fit, reduce font size using binary search
    if (subtitleMetrics.width > maxWidth) {
      let minSize = 20
      let maxSize = subtitleFontSize
      
      // Binary search for the largest font size that fits
      while (maxSize - minSize > 1) {
        const testSize = Math.floor((minSize + maxSize) / 2)
        ctx.font = `${testSize}px "Oswald", Arial, sans-serif`
        const testMetrics = ctx.measureText(subtitle)
        
        if (testMetrics.width <= maxWidth) {
          minSize = testSize
        } else {
          maxSize = testSize
        }
      }
      
      subtitleFontSize = minSize
      ctx.font = `${subtitleFontSize}px "Oswald", Arial, sans-serif`
      subtitleMetrics = ctx.measureText(subtitle)
    }
    
    // Use the smaller of the two font sizes to keep them consistent
    if (subtitleFontSize < mainFontSize) {
      mainFontSize = subtitleFontSize
      // Recalculate main metrics with new size
      ctx.font = `${mainFontSize}px "Oswald", Arial, sans-serif`
      mainMetrics = ctx.measureText(mainHeadline.toUpperCase())
    } else {
      subtitleFontSize = mainFontSize
    }
    
    // Wrap subtitle if still too long
    if (subtitleMetrics.width > maxWidth) {
      const words = subtitle.split(' ')
      let currentLine = words[0]
      
      for (let i = 1; i < words.length; i++) {
        const testLine = currentLine + ' ' + words[i]
        const testMetrics = ctx.measureText(testLine)
        
        if (testMetrics.width > maxWidth && currentLine.length > 0) {
          subtitleLines.push(currentLine)
          currentLine = words[i]
        } else {
          currentLine = testLine
        }
      }
      subtitleLines.push(currentLine)
    } else {
      subtitleLines = [subtitle]
    }
  }
  
  // Add vertical padding (top and bottom) - ensure text fits within box
  // Use less top padding for two-line titles to reduce extra space
  const numLinesForPadding = headlineLines.length
  const topPadding = numLinesForPadding === 1
    ? Math.floor(headlineBoxHeight * 0.12)  // 12% for single line
    : Math.floor(headlineBoxHeight * 0.025)  // 2.5% for two lines
  const bottomPadding = numLinesForPadding === 1
    ? Math.floor(headlineBoxHeight * 0.10)  // 10% for single line
    : Math.floor(headlineBoxHeight * 0.01)  // 1% for two lines (reduced padding on second line)
  const availableHeight = headlineBoxHeight - topPadding - bottomPadding
  
  // Calculate initial line heights
  let mainLineHeight = mainFontSize * 1.3
  let subtitleLineHeight = subtitleFontSize > 0 ? subtitleFontSize * 1.3 : 0
  let finalLineSpacing = 0 // No spacing between first and second line
  
  // Calculate total height needed for all text
  let totalTextHeight = (mainLines.length * mainLineHeight) + finalLineSpacing + (subtitleLines.length * subtitleLineHeight)
  
  // Ensure text fits within available height - reduce font size if needed
  if (totalTextHeight > availableHeight) {
    // Calculate scale factor to fit text
    const scaleFactor = availableHeight / totalTextHeight * 0.95 // 95% to add safety margin
    const adjustedFontSize = Math.floor(mainFontSize * scaleFactor)
    
    // Update font sizes
    mainFontSize = adjustedFontSize
    subtitleFontSize = adjustedFontSize
    
    // Recalculate line heights with adjusted size
    mainLineHeight = mainFontSize * 1.3
    subtitleLineHeight = subtitleFontSize * 1.3
      finalLineSpacing = 0 // No spacing between first and second line
    totalTextHeight = (mainLines.length * mainLineHeight) + finalLineSpacing + (subtitleLines.length * subtitleLineHeight)
  }
  
  // Calculate starting Y position - ensure text fits within padded area
  let startY
  if (subtitleLines.length > 0) {
    // For two lines: position from top with minimal padding, ensure bottom fits
    const lastLineBottom = headlineBoxY + headlineBoxHeight - bottomPadding
    startY = headlineBoxY + topPadding + mainLineHeight / 2
    
    // Check if bottom line fits, adjust if needed
    const subtitleStartY = startY + (mainLines.length * mainLineHeight) + finalLineSpacing
    const subtitleBottom = subtitleStartY + subtitleLineHeight / 2
    
    if (subtitleBottom > lastLineBottom) {
      // Need to reduce font size or adjust position
      const overflow = subtitleBottom - lastLineBottom
      const reductionFactor = (totalTextHeight - overflow) / totalTextHeight
      const newFontSize = Math.max(20, Math.floor(mainFontSize * reductionFactor * 0.98))
      mainFontSize = newFontSize
      subtitleFontSize = newFontSize
      mainLineHeight = mainFontSize * 1.3
      subtitleLineHeight = subtitleFontSize * 1.3
      finalLineSpacing = 0 // No spacing between first and second line
      totalTextHeight = (mainLines.length * mainLineHeight) + finalLineSpacing + (subtitleLines.length * subtitleLineHeight)
      startY = headlineBoxY + topPadding + mainLineHeight / 2
    }
  } else {
    // For single line: center it in available space
    startY = headlineBoxY + topPadding + (availableHeight - totalTextHeight) / 2 + mainLineHeight / 2
  }
  
  // Draw main headline lines
  ctx.fillStyle = '#000000'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.font = `${mainFontSize}px "Oswald", Arial, sans-serif`
  
  mainLines.forEach((line, index) => {
    ctx.fillText(line, textX, startY + index * mainLineHeight)
  })
  
  // Draw subtitle lines if present
  if (subtitleLines.length > 0) {
    ctx.font = `${subtitleFontSize}px "Oswald", Arial, sans-serif`
    const subtitleStartY = startY + (mainLines.length * mainLineHeight) + finalLineSpacing
    
    subtitleLines.forEach((line, index) => {
      ctx.fillText(line, textX, subtitleStartY + index * subtitleLineHeight)
    })
  }
}

function drawTicker(ctx, ticker, width, height, currentTime = null) {
  const tickerHeight = Math.floor(height * 0.08)
  const tickerY = height - tickerHeight
  
  // Black background
  ctx.fillStyle = '#000000'
  ctx.fillRect(0, tickerY, width, tickerHeight)
  
  // Get EST time in 12-hour format (use provided time or get current EST time)
  let hours, minutes, ampm
  if (currentTime) {
    // Use provided EST time - convert to 12-hour format
    const estHours24 = currentTime.getHours()
    hours = estHours24 === 0 ? 12 : (estHours24 > 12 ? estHours24 - 12 : estHours24)
    minutes = currentTime.getMinutes().toString().padStart(2, '0')
    ampm = estHours24 >= 12 ? 'PM' : 'AM'
  } else {
    // Fallback: get EST time if not provided using Intl API
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
    const parts = formatter.formatToParts(new Date())
    hours = parts.find(p => p.type === 'hour').value
    minutes = parts.find(p => p.type === 'minute').value.padStart(2, '0')
    ampm = parts.find(p => p.type === 'dayPeriod')?.value.toUpperCase() || 'AM'
  }
  
  const timeString = `${hours}:${minutes} ${ampm}`
  
  const fontSize = Math.floor(tickerHeight * 0.5)
  ctx.font = `bold ${fontSize}px Arial, sans-serif`
  ctx.textBaseline = 'middle'
  const textY = tickerY + tickerHeight / 2
  
  // Draw time on the left - white text
  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'left'
  const timeX = Math.floor(width * 0.02)
  ctx.fillText(timeString, timeX, textY)
  
  // Draw separator - white text
  const separatorX = timeX + ctx.measureText(timeString).width + Math.floor(width * 0.02)
  ctx.fillText('|', separatorX, textY)
  
  // Draw ticker text on the right of time - white text
  const tickerX = separatorX + ctx.measureText('|').width + Math.floor(width * 0.02)
  const maxTextWidth = width - tickerX - Math.floor(width * 0.02)
  
  // Convert to uppercase
  const upperTicker = ticker.toUpperCase()
  let displayText = upperTicker
  
  // If text is too long, truncate with ellipsis
  const metrics = ctx.measureText(displayText)
  if (metrics.width > maxTextWidth) {
    while (ctx.measureText(displayText + '...').width > maxTextWidth && displayText.length > 0) {
      displayText = displayText.slice(0, -1)
    }
    displayText += '...'
  }
  
  ctx.fillText(displayText, tickerX, textY)
}
