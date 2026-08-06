import { useState } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import ArticleGrid from './components/ArticleGrid'
import Footer from './components/Footer'

function App() {
  const [searchText, setSearchText] = useState('')
  const [isDarkMode, setIsDarkMode] = useState(false)

  return (
    <div className={`app-container ${isDarkMode ? 'dark' : ''}`}>
      <Header isDarkMode={isDarkMode} setIsDarkMode={setIsDarkMode} />
      <main>
        <Hero />
        <ArticleGrid searchText={searchText} />
      </main>
      <Footer searchText={searchText} setSearchText={setSearchText} />
    </div>
  )
}

export default App
