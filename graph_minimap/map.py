import logging
import sys
import time
import sqlite3
import numpy as np
from pathos.multiprocessing import Pool
from Bio.Seq import Seq

print_debug=False
debug_read = False
if len(sys.argv) > 6:
    debug_read = sys.argv[6]

if debug_read:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    logging.debug("Will debug read %s" % debug_read)
    print_debug=True
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

n_threads = int(sys.argv[4])
logging.info("Initing db")
from graph_minimap.mapper import map_read, read_graphs, get_correct_positions, read_fasta
from graph_minimap.numpy_based_minimizer_index import NumpyBasedMinimizerIndex

index_file = sys.argv[2]
index = NumpyBasedMinimizerIndex.from_file(index_file)

n_correct_chain_found = 0
n_best_chain_is_correct = 0
n_best_chain_among_top_half = 0
n_correctly_aligned = 0
n_aligned = 0
n_secondary_correct = 0
n_mapq_60 = 0
n_mapq_60_and_wrong = 0

logging.info("Reading graph numpy arrays")
graph_data = np.load(sys.argv[3])
nodes = graph_data["nodes"]
sequences = graph_data["sequences"]
edges_indexes = graph_data["edges_indexes"]
edges_edges = graph_data["edges_edges"]
edges_n_edges = graph_data["edges_n_edges"]
logging.info("All graph data read")

# Get index numpy arrays
index_hasher_array = np.concatenate([index.hasher._hashes, np.array([2e32-1])])  # An extra element for lookup for indexes that are too large
index_hash_to_index_pos = index._hash_to_index_pos_dict
index_hash_to_n_minimizers = index._hash_to_n_minimizers_dict
index_chromosomes = index._chromosomes
index_positions = index._linear_ref_pos
index_nodes = index._nodes
index_offsets = index._offsets
nodes_to_dist = graph_data["node_to_linear_offsets"]
dist_to_nodes = graph_data["linear_offsets_to_nodes"]


correct_positions = get_correct_positions()
n_minimizers_tot = 0


def map_read_wrapper(fasta_entry):
    name, sequence = fasta_entry
    if print_debug and name != debug_read:
        return name, None

    reverse_sequence = str(Seq(sequence).reverse_complement())
    alignments = []
    n_chains_init = 0
    for seq in [sequence, reverse_sequence]:
        alignment = map_read(seq,
                        index_hasher_array,
                        index_hash_to_index_pos,
                        index_hash_to_n_minimizers,
                        index_chromosomes,
                        index_positions,
                        index_nodes,
                        index_offsets,
                        nodes,
                        sequences,
                        edges_indexes,
                        edges_edges,
                        edges_n_edges,
                        nodes_to_dist,
                        dist_to_nodes,
                        k=21,
                        w=10,
                        print_debug=print_debug,
                        n_chains_init=n_chains_init,
                        min_chain_score=10,
                        skip_minimizers_more_frequent_than=2500
                        )
        n_chains_init += alignment.chains.n_chains
        alignments.append(alignment)
    final_alignment = alignments[0]
    final_alignment.alignments.extend(alignments[1].alignments)
    final_alignment.set_primary_alignment()
    final_alignment.set_mapq()
    final_alignment.name = name
    final_alignment.text_line = final_alignment.to_text_line()
    return name, final_alignment


def map_all():
    all_alignments = []
    fasta_entries = ([entry[0], entry[1]] for entry in read_fasta(sys.argv[1]))
    out_file_name = sys.argv[5]
    out_file = open(out_file_name, "w")

    if n_threads == 1:
        map_function = map
        logging.info("Not running in parallel")
    else:
        logging.info("Creating pool of %d workers" % n_threads)
        pool = Pool(n_threads)
        logging.info("Pool crreated")
        map_function = pool.imap_unordered
    i = 0
    for name, alignment in map_function(map_read_wrapper, fasta_entries):
        if alignment is None:  # For debugging only
            continue
        if i % 1000 == 0:
            logging.info("%d processed" % i)


        alignment.name = name
        out_file.writelines([alignment.text_line])

        #all_alignments.append((name, alignment))
        i += 1

        if False and len(alignment.chains.chromosomes) == 1 and alignment.chains.scores[0] == 1:
            logging.warning("%s has 1 chain with 1 anchor" % name)
            #print([int(m) for m in alignment.chains.minimizer_hashes])

        if print_debug:
            break
        #if i >= 9900:
        #    logging.info("Breaking")
        #    break

    if n_threads > 1:
        logging.info("Closing pool")
        pool.close()
        time.sleep(3)
        logging.info("Pool closed")
    return all_alignments


logging.info("Mapping all reads")
#all_alignments = map_all()
logging.info("Getting alignment stats")

