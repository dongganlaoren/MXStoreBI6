// app/static/js/script.js

// 获取所有数量调节器
const numberAdjusters = document.querySelectorAll('.number-adjuster');

numberAdjusters.forEach(adjuster => {
    // 获取输入框和按钮
    const input = adjuster.querySelector('input');
    const incrementButton = adjuster.querySelector('.increment');
    const decrementButton = adjuster.querySelector('.decrement');

    // 增加按钮点击事件
    incrementButton.addEventListener('click', () => {
        let value = parseFloat(input.value) || 0;
        input.value = value + 1;
    });

    // 减少按钮点击事件
    decrementButton.addEventListener('click', () => {
        let value = parseFloat(input.value) || 0;
        input.value = value - 1;
    });
});