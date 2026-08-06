import Header from './components/Header'
import Hero from './components/Hero'
import ArticleGrid from './components/ArticleGrid'
import Footer from './components/Footer'

function App() {
  return (
    <div className="app-container">
      <Header />
      <main>
        <Hero />
        <ArticleGrid />
      </main>
      <Footer />
    </div>
  )
}

export default App
