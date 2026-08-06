function ArticleCard({ title, excerpt }) {
  return (
    <article className="card">
      <h2>{title}</h2>
      <p>{excerpt}</p>
      <a href="#">자세히 보기</a>
    </article>
  )
}

export default ArticleCard
