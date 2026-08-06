// 함수에 "props"를 인자로 추가합니다. 이름은 무엇이든 가능하지만, "props"가 관례입니다.
function AlertButton(props) {
    return (
        // 중괄호 { } 를 사용해 JavaScript 변수를 JSX 안에 주입합니다
        <button className="custom-btn">
            {props.text}
        </button>
    );
}

export default AlertButton;