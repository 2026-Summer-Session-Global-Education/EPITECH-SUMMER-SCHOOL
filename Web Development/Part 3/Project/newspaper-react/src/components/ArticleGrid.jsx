import ArticleCard from './ArticleCard'

function ArticleGrid({ searchText }) {
  const articles = [
    {
      id: 1,
      title: 'Strengthening Climate Crisis Response',
      excerpt: 'The government announced a new policy to achieve its carbon neutrality goals.',
    },
    {
      id: 2,
      title: 'AI Startup Investment Rising',
      excerpt: 'Global investors are increasing their interest in artificial intelligence companies.',
    },
    {
      id: 3,
      title: 'Local Festival Thrives',
      excerpt: 'Summer festivals in major cities are drawing large crowds of residents.',
    },
  ]

  const filteredArticles = articles.filter((article) => {
    const query = searchText.toLowerCase()
    if (!query) return true

    return (
      article.title.toLowerCase().includes(query) ||
      article.excerpt.toLowerCase().includes(query)
    )
  })

  return (
    <section className="article-grid">
      {filteredArticles.length > 0 ? (
        filteredArticles.map((article) => (
          <ArticleCard key={article.id} title={article.title} excerpt={article.excerpt} />
        ))
      ) : (
        <p className="empty-state">No articles match your search.</p>
      )}
    </section>
  )
}

export default ArticleGrid
