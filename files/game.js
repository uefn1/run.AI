const BOARD_SIZE = 8;
const BLACK = 1;
const WHITE = -1;
const EMPTY = 0;

let board = [];
let currentPlayer = BLACK;
let isAiThinking = false;
let isGameOver = false;
let gameId = 0;

const boardEl = document.getElementById('board');
const blackScoreEl = document.getElementById('black-score');
const whiteScoreEl = document.getElementById('white-score');
const turnIndicator = document.getElementById('turn-indicator');
const messageEl = document.getElementById('message');
const resetBtn = document.getElementById('reset-btn');

const weights = [
    [100, -20, 10, 5, 5, 10, -20, 100],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [10, -2, 15, 3, 3, 15, -2, 10],
    [5, -2, 3, 0, 0, 3, -2, 5],
    [5, -2, 3, 0, 0, 3, -2, 5],
    [10, -2, 15, 3, 3, 15, -2, 10],
    [-20, -50, -2, -2, -2, -2, -50, -20],
    [100, -20, 10, 5, 5, 10, -20, 100]
];

function initGame() {
    gameId++;
    board = Array(BOARD_SIZE).fill(null).map(() => Array(BOARD_SIZE).fill(EMPTY));
    board[3][3] = WHITE;
    board[4][4] = WHITE;
    board[3][4] = BLACK;
    board[4][3] = BLACK;
    currentPlayer = BLACK;
    isAiThinking = false;
    isGameOver = false;
    messageEl.textContent = '';
    resetBtn.classList.remove('game-over-btn');
    boardEl.style.pointerEvents = 'auto';
    updateStatus();
    renderBoard();
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

function renderBoard() {
    boardEl.innerHTML = '';
    const validMoves = (currentPlayer === BLACK && !isAiThinking && !isGameOver) ? getValidMoves(board, BLACK) : [];

    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            if (validMoves.some(m => m.r === r && m.c === c)) {
                cell.classList.add('hint');
            } else {
                cell.onclick = () => handleCellClick(r, c);
            }
            const piece = document.createElement('div');
            piece.className = 'piece';
            if (board[r][c] === BLACK) piece.classList.add('black');
            if (board[r][c] === WHITE) piece.classList.add('white');
            cell.appendChild(piece);
            boardEl.appendChild(cell);
        }
    }
}

function handleCellClick(r, c) {
    if (isGameOver || currentPlayer !== BLACK || isAiThinking) return;
    if (makeMove(board, r, c, BLACK)) {
        boardEl.style.pointerEvents = 'none';
        messageEl.textContent = '';
        currentPlayer = WHITE;
        updateStatus();
        renderBoard();
        const currentGameId = gameId;
        setTimeout(() => {
            if (currentGameId !== gameId || isGameOver) return;
            if (currentPlayer === WHITE) {
                if (canMove(board, WHITE)) {
                    startAiTurn();
                } else {
                    checkPass(WHITE);
                }
            }
        }, 600);
    }
}

function startAiTurn() {
    isAiThinking = true;
    boardEl.style.pointerEvents = 'none';
    turnIndicator.textContent = "AIが思考中...";
    renderBoard();
    const currentGameId = gameId;
    setTimeout(() => {
        if (currentGameId === gameId) aiMove();
    }, 600);
}

function aiMove() {
    if (isGameOver || currentPlayer !== WHITE || !isAiThinking) return;
    const bestMove = getBestMove(board, WHITE);
    if (bestMove) {
        makeMove(board, bestMove.r, bestMove.c, WHITE);
        currentPlayer = BLACK;
        isAiThinking = false;
        if (canMove(board, BLACK)) {
            messageEl.textContent = '';
            updateStatus();
            renderBoard();
            boardEl.style.pointerEvents = 'auto';
        } else {
            checkPass(BLACK);
        }
    } else {
        checkPass(WHITE);
    }
}

function checkPass(player) {
    const nextPlayer = player === BLACK ? WHITE : BLACK;
    if (canMove(board, nextPlayer)) {
        messageEl.textContent = `${player === BLACK ? '黒' : '白'}はパスしました`;
        currentPlayer = nextPlayer;
        isAiThinking = false;
        updateStatus();
        renderBoard();
        if (currentPlayer === WHITE) {
            const currentGameId = gameId;
            setTimeout(() => {
                if (currentGameId === gameId) startAiTurn();
            }, 1000);
        } else {
            boardEl.style.pointerEvents = 'auto';
        }
    } else {
        isGameOver = true;
        const scores = calculateScores();
        const winner = scores.black > scores.white ? '黒' : (scores.white > scores.black ? '白' : '引き分け');
        const diff = Math.abs(scores.black - scores.white);
        messageEl.textContent = `ゲーム終了！ 勝者: ${winner} (黒:${scores.black} 白:${scores.white} 差:${diff})`;
        turnIndicator.textContent = "Game Over";
        resetBtn.classList.add('game-over-btn');
        boardEl.style.pointerEvents = 'none';
        updateStatus();
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
            if (canPlace(board, r, c, player)) moves.push({ r, c });
        }
    }
    return moves;
}

function canPlace(board, r, c, player) {
    if (board[r][c] !== EMPTY) return false;
    const opponent = -player;
    const directions = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]];
    for (let [dr, dc] of directions) {
        let nr = r + dr, nc = c + dc;
        let hasOpponentBetween = false;
        while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === opponent) {
            nr += dr; nc += dc;
            hasOpponentBetween = true;
        }
        if (hasOpponentBetween && nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === player) return true;
    }
    return false;
}

function makeMove(board, r, c, player) {
    if (!canPlace(board, r, c, player)) return false;
    board[r][c] = player;
    const opponent = -player;
    const directions = [[-1,-1], [-1,0], [-1,1], [0,1], [0,-1], [1,-1], [1,0], [1,1]];
    for (let [dr, dc] of directions) {
        let nr = r + dr, nc = c + dc;
        let cellsToFlip = [];
        while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === opponent) {
            cellsToFlip.push({ r: nr, c: nc });
            nr += dr; nc += dc;
        }
        if (cellsToFlip.length > 0 && nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === player) {
            for (let cell of cellsToFlip) board[cell.r][cell.c] = player;
        }
    }
    return true;
}

function applyMoveMinimax(board, r, c, player) {
    const opponent = -player;
    const flipped = [];
    board[r][c] = player;
    const directions = [[-1,-1], [-1,0], [-1,1], [0,1], [0,-1], [1,-1], [1,0], [1,1]];
    for (let [dr, dc] of directions) {
        let nr = r + dr, nc = c + dc;
        let cellsToFlip = [];
        while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === opponent) {
            cellsToFlip.push({ r: nr, c: nc });
            nr += dr; nc += dc;
        }
        if (cellsToFlip.length > 0 && nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === player) {
            for (let cell of cellsToFlip) board[cell.r][cell.c] = player;
            flipped.push(...cellsToFlip);
        }
    }
    return flipped;
}

function undoMove(board, r, c, player, flipped) {
    board[r][c] = EMPTY;
    for (let cell of flipped) board[cell.r][cell.c] = -player;
}

function getBestMove(board, player) {
    const moves = getValidMoves(board, player);
    if (moves.length === 0) return null;
    const totalPieces = board.flat().filter(p => p !== EMPTY).length;
    const depth = totalPieces > 50 ? 6 : (totalPieces > 30 ? 4 : 3);
    let bestScore = -Infinity, bestMove = moves[0];
    for (let move of moves) {
        const flipped = applyMoveMinimax(board, move.r, move.c, player);
        const score = minimax(board, depth, -Infinity, Infinity, false);
        undoMove(board, move.r, move.c, player, flipped);
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
        const opponent = -player;
        if (!canMove(board, opponent)) return evaluateBoard(board);
        return minimax(board, depth - 1, alpha, beta, !isMaximizing);
    }
    if (isMaximizing) {
        let maxEval = -Infinity;
        for (let move of moves) {
            const flipped = applyMoveMinimax(board, move.r, move.c, WHITE);
            const evaluation = minimax(board, depth - 1, alpha, beta, false);
            undoMove(board, move.r, move.c, WHITE, flipped);
            maxEval = Math.max(maxEval, evaluation);
            alpha = Math.max(alpha, evaluation);
            if (beta <= alpha) break;
        }
        return maxEval;
    } else {
        let minEval = Infinity;
        for (let move of moves) {
            const flipped = applyMoveMinimax(board, move.r, move.c, BLACK);
            const evaluation = minimax(board, depth - 1, alpha, beta, true);
            undoMove(board, move.r, move.c, BLACK, flipped);
            minEval = Math.min(minEval, evaluation);
            beta = Math.min(beta, minEval);
            if (beta <= alpha) break;
        }
        return minEval;
    }
}

function evaluateBoard(board) {
    let score = 0, whitePieces = 0, blackPieces = 0;
    const stable = getStableDiscs(board);
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            if (board[r][c] === WHITE) {
                score += weights[r][c];
                whitePieces++;
                if (stable[r][c]) score += 150;
            } else if (board[r][c] === BLACK) {
                score -= weights[r][c];
                blackPieces++;
                if (stable[r][c]) score -= 150;
            }
        }
    }
    if (whitePieces + blackPieces > 40) {
        score += (whitePieces - blackPieces) * 50;
    } else {
        const whiteMoves = getValidMoves(board, WHITE).length;
        const blackMoves = getValidMoves(board, BLACK).length;
        score += (whiteMoves - blackMoves) * 25;
    }
    return score;
}

function getStableDiscs(board) {
    const stableDiscs = Array(BOARD_SIZE).fill(null).map(() => Array(BOARD_SIZE).fill(false));
    let changed = true;
    while (changed) {
        changed = false;
        for (let r = 0; r < BOARD_SIZE; r++) {
            for (let c = 0; c < BOARD_SIZE; c++) {
                if (board[r][c] === EMPTY || stableDiscs[r][c]) continue;
                if (isDiscStable(board, r, c, stableDiscs)) {
                    stableDiscs[r][c] = true;
                    changed = true;
                }
            }
        }
    }
    return stableDiscs;
}

function isDiscStable(board, r, c, stableDiscs) {
    const player = board[r][c];
    const opponent = -player;
    const directions = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]];
    for (let [dr, dc] of directions) {
        let nr = r + dr, nc = c + dc;
        let hasOpponentBetween = false;
        while (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && (board[nr][nc] === opponent || stableDiscs[nr][nc])) {
            if (board[nr][nc] === opponent) hasOpponentBetween = true;
            nr += dr; nc += dc;
        }
        if (hasOpponentBetween && nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE && board[nr][nc] === player) {
            // This disc can still be flipped
            return false;
        }
    }
    // No direction allows this disc to be flipped
    return true;
}

function calculateScores() {
    let black = 0, white = 0;
    for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
            if (board[r][c] === BLACK) black++;
            else if (board[r][c] === WHITE) white++;
        }
    }
    return { black, white };
}

resetBtn.onclick = initGame;

window.onload = initGame;