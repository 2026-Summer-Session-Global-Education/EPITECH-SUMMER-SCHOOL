import { useState } from 'react'

function ArticleCard({ title, excerpt }) {
  const [likeCount, setLikeCount] = useState(0)

  return (
    <article className="card">
      <h2>{title}</h2>
      <p>{excerpt}</p>
      <button
        type="button"
        className="like-button"
        onClick={() => setLikeCount((count) => count + 1)}
      >
        ❤️ Like {likeCount}
      </button>
      <a href="#">Read More</a>
    </article>
  )
}

export default ArticleCard
