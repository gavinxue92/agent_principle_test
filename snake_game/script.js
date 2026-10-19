const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// 设置画布大小
canvas.width = 400;
canvas.height = 400;

// 蛇和食物的初始位置
let snake = [{x: 200, y: 200}];
let food = {x: 0, y: 0};
let dx = 20;
let dy = 0;
let speed = 150;
let score = 0;

// 生成随机食物位置
function generateFood() {
    food.x = Math.floor(Math.random() * canvas.width / 20) * 20;
    food.y = Math.floor(Math.random() * canvas.height / 20) * 20;
}

// 游戏主循环
function gameLoop() {
    if (checkCollision()) return;
    
    // 更新蛇的位置
    const head = {x: snake[0].x + dx, y: snake[0].y + dy};
    snake.unshift(head);
    
    // 检查是否吃到食物
    if (snake[0].x === food.x && snake[0].y === food.y) {
        score++;
        generateFood();
    } else {
        snake.pop();
    }
    
    // 清屏并重绘画
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 画食物
    ctx.fillStyle = 'red';
    ctx.fillRect(food.x, food.y, 20, 20);
    
    // 画蛇
    ctx.fillStyle = '#4CAF50';
    snake.forEach(segment => {
        ctx.fillRect(segment.x, segment.y, 20, 20);
    });
    
    // 显示分数
    ctx.fillStyle = 'white';
    ctx.font = '20px Arial';
    ctx.fillText('分数: ' + score, 10, 30);
    
    setTimeout(gameLoop, speed);
}

// 检查碰撞
function checkCollision() {
    // 撞墙
    if (snake[0].x < 0 || snake[0].x >= canvas.width || 
        snake[0].y < 0 || snake[0].y >= canvas.height) {
        gameOver();
        return true;
    }
    
    // 撞自己
    for (let i = 1; i < snake.length; i++) {
        if (snake[i].x === snake[0].x && snake[i].y === snake[0].y) {
            gameOver();
            return true;
        }
    }
    return false;
}

// 游戏结束
function gameOver() {
    ctx.fillStyle = 'white';
    ctx.font = '30px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('游戏结束!', canvas.width / 2, canvas.height / 2);
}

// 键盘控制
document.addEventListener('keydown', e => {
    switch(e.key) {
        case 'ArrowUp':
            if (dy === 0) { dx = 0; dy = -20; }
            break;
        case 'ArrowDown':
            if (dy === 0) { dx = 0; dy = 20; }
            break;
        case 'ArrowLeft':
            if (dx === 0) { dx = -20; dy = 0; }
            break;
        case 'ArrowRight':
            if (dx === 0) { dx = 20; dy = 0; }
            break;
    }
});

// 初始化游戏
generateFood();
gameLoop();