import { useState } from 'react'
import NewsGenerator from './components/NewsGenerator'
import './App.css'

function App() {
  return (
    <div className="App">
      <header className="app-header">
        <h1>Break Your Own News</h1>
        <p className="subtitle">The Breaking News Generator - Today's top story... you!</p>
      </header>
      <NewsGenerator />
      <footer className="app-footer">
        <p>This app is intended for fun, humour and parody - be careful what you make and how it may be shared.</p>
        <p>You should avoid making things which are unlawful, defamatory or likely to cause distress. Have fun and be kind!</p>
      </footer>
    </div>
  )
}

export default App
