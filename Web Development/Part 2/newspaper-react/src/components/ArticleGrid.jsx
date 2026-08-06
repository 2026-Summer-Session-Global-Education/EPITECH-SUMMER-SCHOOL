import ArticleCard from './ArticleCard'

function ArticleGrid() {
  return (
    <section className="article-grid">
      <ArticleCard title="기후 위기 대응 강화" excerpt="정부가 탄소중립 목표 달성을 위해 새로운 정책을 발표했습니다." />
      <ArticleCard title="AI 스타트업 투자 증가" excerpt="글로벌 투자자들이 인공지능 분야 기업에 대한 관심을 높이고 있습니다." />
      <ArticleCard title="지역 축제 성황" excerpt="주요 도시에서 여름 축제가 시민들로 북적이고 있습니다." />
    </section>
  )
}

export default ArticleGrid
