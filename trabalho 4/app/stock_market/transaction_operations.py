from ..enums import TransactionState
from ..order import Transaction

class TransactionOperation:
    """
    Representa uma transação (sequência de operações)

    :param transaction: Transação a ser operada
    """

    def __init__(self, transaction: Transaction):
        self.state = TransactionState.DESACTIVETED
        self.current_transaction = transaction

        self.set_index()

    def set_index(self):
        #TODO: Abrir o arquivo, pegar o index disponível
        self.id = 0
        
class Coordinator:

    """
    Representa uma coordenador, responsável por iniciar uma transação
    """

    def __init__(self):
        self.transactions_operations: dict[int, TransactionOperation] = {}
        self.participants: dict[int, list[Participant]] = {}
        self.vote_decision: dict[]


    def open_transaction(self, transaction: Transaction, participants: Participant) -> int:
        """
        Cria uma operação de transação

        :param transaction: Transação a ser operada
        :param participant: Participante requerendo a transação
        """
        transaction_operation = TransactionOperation(transaction)
        transaction_id = transaction_operation.id

        buyer_participant = Participant()
        sell_participant = Participant()
        self.participants[transaction_id].append(buyer_participant)
        self.participants[transaction_id].append(sell_participant)
        
        self.transactions_operations.append(transaction_operation)
        
        #TODO: falar para os participantes preparem a transacao
        self.voting_fase(transaction_id)

        return transaction_id

    def get_transaction_state(self, transaction_id):
        return self.transactions_operations[transaction_id].state

    @pyro.expose
    def voting_fase(self, transaction_id):
        votation_result = TransactionState.PENDING
        positives_votes = []
        for participant in self.participants[transaction_id].values():
            vote = participant.vote_for_transaction(transaction_id)
            if (vote): 
                positives_votes.append(vote)

        if len(positives_votes) == len(self.participants[transaction_id].values()):
            self.transactions_operations[transaction_id].state = TransactionState.ACTIVETED
            for participant in self.participants[transaction_id].values():
                participant.make_transaction(transaction_id)
        else:
            for participant in self.participants[transaction_id].values():
                participant.cancel_transaction(transaction_id)
        
        
            


class Participant:
    """
    Representa um participante de uma transação
    """

    def __init__(self):
        pass

    def prepare_transaction(self, transaction_id):
        pass

    def vote_for_transaction(self, transaction_id):
        pass

    def make_transaction(self, transaction_id):
        pass

    def cancel_transaction(self, transaction_id):
        pass