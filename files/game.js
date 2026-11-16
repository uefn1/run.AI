const BOARD_SIZE = 8;
const BLACK = 1;
const WHITE = -1;
const EMPTY = 0;

let board = [];
let currentPlayer = BLACK;
let isAiThinking = false;

const boardEl = document.getElementById('board');
const blackScoreEl = document.getElementById('black-score');
const whiteScoreEl = document.getElementById('white-score');
const turnIndicator = document.getElementById('turn-indicator');
const messageEl = document.getElementById('message');
const resetBtn = document.getElementById('reset-btn');

const weights = [
    [100, -20, 10, 5, 5, 10, -20, 100],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [10, -2, 5, 1, 1, 5, -2, 10],
    [5, -2, 1, 0, 0, 1, -2, 5],
    [5, -2, 1, 0, 0, 1, -2, 5],
    [10, -2, 5, 1, 1, 5, -2, 10],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [100, -20, 10, 5, 5, 10, -20, 100]
];

function initGame() {
    board = Array(BOARD_SIZE).fill(null).map(() => Array(BOARD_SIZE).fill(EMPTY));
    board[3][3] = WHITE;
    board[4][4] = WHITE;
    board[3][4] = BLACK;
    board[4][3] = BLACK;
    currentPlayer = BLACK;
    isAiThinking = false;
    messageEl.textContent = '';
    renderBoard();
    updateStatus();
}

function renderBoard() {
    boardEl.innerHTML = '';
    const validMoves = getValidMoves(board, currentPlayer);

    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            if (currentPlayer === BLACK && validMoves.some(m => m.r === r && m.c === c)) {
                cell.classList.add('hint');
            }
            
            const piece = document.createElement('div');
            piece.className = 'piece';
            if (board[r][c] === BLACK) piece.classList.add('black');
            if (board[r][c] === WHITE) piece.classList.add('white');
            
            cell.appendChild(piece);
            cell.onclick = () => handleCellClick(r, c);
            boardEl.appendChild(cell);
        }
    }
}

function handleCellClick(r, c) {
    if (currentPlayer !== BLACK || isAiThinking) return;

    if (makeMove(board, r, c, BLACK)) {
        currentPlayer = WHITE;
        updateStatus();
        renderBoard();
        
        if (canMove(board, WHITE)) {
            isAiThinking = true;
            turnIndicator.textContent = "AIが思考中...";
            setTimeout(aiMove, 600);
        } else {
            checkPass(WHITE);
        }
    }
}

function aiMove() {
    const bestMove = getBestMove(board, WHITE);
    if (bestMove) {
        makeMove(board, bestMove.r, bestMove.c, WHITE);
    }
    
    currentPlayer = BLACK;
    isAiThinking = false;
    
    if (canMove(board, BLACK)) {
        updateStatus();
        renderBoard();
    } else {
        checkPass(BLACK);
    }
}

function checkPass(player) {
    if (canMove(board, player === BLACK ? WHITE : BLACK)) {
        messageEl.textContent = `${player === BLACK ? '黒' : '白'}はパスしました`;
        currentPlayer = player === BLACK ? WHITE : BLACK;
        updateStatus();
        renderBoard();
        if (currentPlayer === WHITE) {
            isAiThinking = true;
            setTimeout(aiMove, 600);
        }
    } else {
        const scores = calculateScores();
        const winner = scores.black > scores.white ? '黒' : (scores.white > scores.black ? '白' : '引き分け');
        messageEl.textContent = `ゲーム終了！ 勝者: ${winner}`;
        turnIndicator.textContent = "Game Over";
        renderBoard();
    }
}

function canMove(board, player) {
    return getValidMoves(board, player).length > 0;
}

function getValidMoves(board, player) {
    const moves = [];
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            if (canPlace(board, r, c, player)) {
                moves.push({ r, c });
            }
        }
    }
    return moves;
}

function canPlace(board, r, c, player) {
    if (board[r][c] !== EMPTY) return false;
    const opponent = -player;
    const directions = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]];
    
    for (let [dr, dc] of directions) {
        let nr = r + dr;
        let nc = c + dc;
        let hasOpponentBetween = false;
        
        while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === opponent) {
            nr += dr;
            nc += dc;
            hasOpponentBetween = true;
        }
        
        if (hasOpponentBetween && nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === player) {
            return true;
        }
    }
    return false;
}

function makeMove(board, r, c, player) {
    if (!canPlace(board, r, c, player)) return false;
    
    board[r][c] = player;
    const opponent = -player;
    const directions = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]];
    
    for (let [dr, dc] of directions) {
        let nr = r + dr;
        let nc = c + dc;
        let cellsToFlip = [];
        
        while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === opponent) {
            cellsToFlip.push({ r: nr, c: nc });
            nr += dr;
            nc += dc;
        }
        
        if (cellsToFlip.length > 0 && nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === player) {
            for (let cell of cellsToFlip) {
                board[cell.r][cell.c] = player;
            }
        }
    }
    return true;
}

function getBestMove(board, player) {
    const moves = getValidMoves(board, player);
    let bestScore = -Infinity;
    let bestMove = moves[0];

    for (let move of moves) {
        const tempBoard = board.map(row => [...row]);
        makeMove(tempBoard, move.r, move.c, player);
        const score = minimax(tempBoard, 3, -Infinity, Infinity, false);
        if (score > bestScore) {
            bestScore = score;
            bestMove = move;
        }
    }
    return bestMove;
}

function minimax(board, depth, alpha, beta, isMaximizing) {
    if (depth === 0) return evaluateBoard(board);

    const player = isMaximizing ? WHITE : BLACK;
    const moves = getValidMoves(board, player);

    if (moves.length === 0) {
        return minimax(board, depth - 1, alpha, beta, !isMaximizing);
    }

    if (isMaximizing) {
        let maxEval = -Infinity;
        for (let move of moves) {
            const tempBoard = board.map(row => [...row]);
            makeMove(tempBoard, move.r, move.c, WHITE);
            const evaluation = minimax(tempBoard, depth - 1, alpha, beta, false);
            maxEval = Math.max(maxEval, evaluation);
            alpha = Math.max(alpha, evaluation);
            if (beta <= alpha) break;
        }
        return maxEval;
    } else {
        let minEval = Infinity;
        for (let move of moves) {
            const tempBoard = board.map(row => [...row]);
            makeMove(tempBoard, move.r, move.c, BLACK);
            const evaluation = minimax(tempBoard, depth - 1, alpha, beta, true);
            minEval = Math.min(minEval, evaluation);
            beta = Math.min(beta, evaluation);
            if (beta <= alpha) break;
        }
        return minEval;
    }
}

function evaluateBoard(board) {
    let score = 0;
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            if (board[r][c] === WHITE) score += weights[r][c];
            else if (board[r][c] === BLACK) score -= weights[r][c];
        }
    }
    return score;
}

function calculateScores() {
    let black = 0, white = 0;
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            if (board[r][c] === BLACK) black++;
            if (board[r][c] === WHITE) white++;
        }
    }
    return { black, white };
}

function updateStatus() {
    const scores = calculateScores();
    blackScoreEl.textContent = scores.black;
    whiteScoreEl.textContent = scores.white;
    if (currentPlayer === BLACK) {
        turnIndicator.textContent = "あなたの番です (黒)";
    } else {
        turnIndicator.textContent = "AIの番です (白)";
    }
}

resetBtn.onclick = initGame;

initGame();