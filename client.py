import socket

class TicTacToe:
    def __init__(self):
        self.board = [' ' for _ in range(9)]  # 3x3 Tic Tac Toe board (9 positions)
        self.current_winner = None  # None means no winner yet

    def print_board(self):
        """Print the Tic Tac Toe board."""
        for row in [self.board[i:i+3] for i in range(0, 9, 3)]:
            print("| " + " | ".join(row) + " |")
    
    def available_moves(self):
        """Return list of available moves (empty spots on the board)."""
        return [i for i, spot in enumerate(self.board) if spot == ' ']

    def make_move(self, square, letter):
        """Make a move if the square is empty, and check if there's a winner."""
        if self.board[square] == ' ':
            self.board[square] = letter
            if self.winner(square, letter):
                self.current_winner = letter
            return True
        return False

    def winner(self, square, letter):
        """Check if there is a winner after a move."""
        row_ind = square // 3
        row = self.board[row_ind*3:(row_ind+1)*3]
        if all([spot == letter for spot in row]):
            return True

        col_ind = square % 3
        column = [self.board[i] for i in range(col_ind, 9, 3)]
        if all([spot == letter for spot in column]):
            return True

        if square % 2 == 0:
            diagonal1 = [self.board[i] for i in [0, 4, 8]]
            if all([spot == letter for spot in diagonal1]):
                return True
            diagonal2 = [self.board[i] for i in [2, 4, 6]]
            if all([spot == letter for spot in diagonal2]):
                return True
        return False

    def is_full(self):
        """Check if the board is full."""
        return ' ' not in self.board

def start_client():
    """Start the client, connect to server, and play the game."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 5555))
    game = TicTacToe()

    # Receive messages from the server (game status)
    while True:
        message = client.recv(1024).decode()
        print(message)

        if "Your turn" in message:
            move = input("Enter your move (0-8): ")
            client.send(move.encode())  # Send move to the server
        elif "wins" in message or "tie" in message:
            print(message)  # Display the result
            break

if __name__ == "__main__":
    start_client()
