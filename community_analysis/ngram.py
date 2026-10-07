import json, math
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import textwrap
from scipy.stats import chi2_contingency
from answer_tagging.ontology import ontology

START, END = "<S>", "</S>"

community_names = ["AskEconomics", "AskHistorians", "asklinguistics", "history", "ScienceBasedParenting", "beyondthebump", "explainlikeimfive", "NoStupidQuestions", "OutOfTheLoop"]

def extract_sequences(questions):
    seqs = []
    for q in questions:
        for c in q.get("comments", []):
            seq = [s["action_id"] for s in c.get("tagged_segments", []) 
                   if s["action_id"] != "NONE"]
            if seq:
                seqs.append([START] + seq + [END])
    return seqs

class NgramModel:
    def __init__(self, n=2, k=0.01):
        self.n = n
        self.k = k
        self.counts = defaultdict(Counter)
        self.vocab = set()

    def train(self, sequences):
        for seq in sequences:
            self.vocab.update(seq)
            # pad with n-1 START tokens for trigram+ context
            padded = [START] * (self.n - 1) + seq[1:]  # seq already has one START
            for i in range(len(padded) - (self.n - 1)):
                ctx = tuple(padded[i:i + self.n - 1])
                nxt = padded[i + self.n - 1]
                self.counts[ctx][nxt] += 1

    def perplexity(self, sequences):
        log_prob, total = 0.0, 0
        for seq in sequences:
            padded = [START] * (self.n - 1) + seq[1:]
            for i in range(len(padded) - (self.n - 1)):
                ctx = tuple(padded[i:i + self.n - 1])
                nxt = padded[i + self.n - 1]
                c = self.counts[ctx]
                denom = sum(c.values()) + self.k * len(self.vocab)
                p = (c[nxt] + self.k) / denom
                log_prob += math.log2(p)
                total += 1
        return 2 ** (-log_prob / total) if total else float("inf")

    def transition_matrix(self):
        mat = {}
        for ctx, nexts in self.counts.items():
            total = sum(nexts.values())
            mat[ctx] = {b: c / total for b, c in nexts.most_common()}
        return mat


def train_and_compare(communities: dict, n=2):
    """
    communities: {name: [list of question dicts]}
    n: 2 for bigram, 3 for trigram, etc.
    Returns: (models dict, sequences dict, perplexity DataFrame)
    """
    seqs = {name: extract_sequences(qs) for name, qs in communities.items()}
    models = {}
    for name, s in seqs.items():
        m = NgramModel(n=n)
        m.train(s)
        models[name] = m
        ntoks = sum(len(x) - 1 for x in s)
        print(f"{name}: {len(s)} sequences, {ntoks} tokens, n={n}")

    names = sorted(communities.keys())
    matrix = pd.DataFrame(
        [[models[t].perplexity(seqs[e]) for e in names] for t in names],
        index=names, columns=names,
    )
    matrix.index.name, matrix.columns.name = "train", "eval"
    return models, seqs, matrix


def plot_perplexity_heatmap(matrix, train_names, eval_names, title, save=False, save_name='plot.pdf', wrap_yticks=False, wrap_width=15, fig_size=(8, 6), ax=None, wrap_xticks=False):
    sub = matrix.loc[train_names, eval_names]
    is_square = (train_names == eval_names)

    if ax is None:
        fig, ax = plt.subplots(figsize=fig_size)
        standalone = True
    else:
        standalone = False

    if is_square:
        sns.heatmap(sub, annot=True, fmt=".1f", cmap="YlOrRd",
                    ax=ax, cbar_kws={"label": "Perplexity", "pad": 0.02, "shrink": 0.8})
        for i in range(len(sub)):
            ax.add_patch(plt.Rectangle((i, i), 1, 1, fill=False,
                           edgecolor="black", linewidth=1, linestyle="--"))
    else:
        sns.heatmap(sub, annot=True, fmt=".1f", cmap="YlOrRd",
                    ax=ax, cbar_kws={"label": "Perplexity", "pad": 0.02, "shrink": 0.8})

    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)

    if wrap_yticks:
        wrapped = [label.get_text().replace('-', '-\n', 1) for label in ax.get_yticklabels()]
        ax.set_yticklabels(wrapped, rotation=0, fontsize=8)
    else:
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8)
        
    if wrap_xticks:
        def wrap_label(text):
            if "mimic-" in text:
                return text.replace("mimic-", "mimic-\n", 1)
            elif text.startswith("sonnet-"):
                return text.replace("sonnet-", "sonnet-\n", 1)
            return text
        wrapped_x = [wrap_label(label.get_text()) for label in ax.get_xticklabels()]
        ax.set_xticklabels(wrapped_x, rotation=45, ha="right", fontsize=8)

    ax.set_xlabel("Evaluated on", labelpad=-10, fontweight="bold")
    ax.set_ylabel("Trained on", fontweight="bold")
    if title:
        ax.set_title(title)

    if standalone:
        plt.tight_layout()
        if save:
            plt.savefig(save_name)
        plt.show()
    
    


def find_subreddit_specific_bigrams(models, threshold=10):
    """For each subreddit, finds bigrams that are distinctively 
    over-represented compared to all subreddits combined -> use an informative Dirichlet prior where the prior for each bigram is its background frequency.
    # look here: https://github.com/jmhessel/FightingWords/blob/master/fighting_words.py
    """
    
    # Pool all subreddits to get background counts
    all_subs_counts = defaultdict(Counter)
    for model in models.values():
        for curr_act, next_acts in model.counts.items():
            all_subs_counts[curr_act].update(next_acts)
    
    all_subs_total = sum(sum(c.values()) for c in all_subs_counts.values())
    
    results = {}
    
    # for each subreddit, compute z-scores
    for sub_name, model in models.items():
        z_scores = []
        this_sub_total = sum(sum(c.values()) for c in model.counts.values())
        
        for curr_act, next_acts in model.counts.items():
            for next_act, this_sub_count in next_acts.items():
                
                if this_sub_count < threshold:
                    continue
                
                all_subs_count = all_subs_counts[curr_act][next_act]
                
                # dirichlet prior? use background frequency as fake counts
                prior = all_subs_count
                prior_total = all_subs_total
                
                # smoothed log-odds for this subreddit
                this_sub_smoothed = this_sub_count + prior
                this_sub_denom = this_sub_total + prior_total
                this_sub_log_odds = np.log(this_sub_smoothed / (this_sub_denom - this_sub_smoothed))
                
                # smoothed log-odds for all subreddits
                all_subs_smoothed = all_subs_count + prior
                all_subs_denom = all_subs_total + prior_total
                all_subs_log_odds = np.log(all_subs_smoothed / (all_subs_denom - all_subs_smoothed))
                
                # z-score
                log_odds_diff = this_sub_log_odds - all_subs_log_odds
                uncertainty = 1 / this_sub_smoothed + 1 / all_subs_smoothed
                z = log_odds_diff / np.sqrt(uncertainty)
                
                z_scores.append({
                    "from": curr_act[0],
                    "to": next_act,
                    "z_score": z,
                    "count": this_sub_count
                })
        
        results[sub_name] = sorted(z_scores, key=lambda x: x['z_score'], reverse=True)
    
    return results

def plot_two_subs(models, ontology, sub1, sub2):
    action_to_family = {}
    action_to_name = {}
    for entry in ontology:
        if entry["id"] != "NONE":
            action_to_family[entry["id"]] = entry["action_family_abbr"]
            action_to_name[entry["id"]] = entry["name"]
    
    family_order = ["SI", "CQ", "AQ", "RQ", "NO"]
    family_bg_colors = {
        "SI": "#fce4e4",
        "CQ": "#fef3d5",
        "AQ": "#d5f5e3",
        "RQ": "#d4eaf7",
        "NO": "#e8e9eb"
    }
    
    sub1_color = "#2c3e50"
    sub2_color = "#e74c3c"
    
    def get_counts(model):
        action_counts = Counter()
        for ctx, nexts in model.counts.items():
            for act, count in nexts.items():
                if act in action_to_family and act not in ("<S>", "</S>", "NONE"):
                    action_counts[act] += count
        return action_counts
    
    counts1 = get_counts(models[sub1])
    counts2 = get_counts(models[sub2])
    total1 = sum(counts1.values())
    total2 = sum(counts2.values())
    
    props1 = {a: counts1.get(a, 0) / total1 for a in action_to_family}
    props2 = {a: counts2.get(a, 0) / total2 for a in action_to_family}
    
    actions = sorted(action_to_family.keys(),
                     key=lambda a: (family_order.index(action_to_family[a]), a))
    actions = [a for a in actions if counts1.get(a, 0) + counts2.get(a, 0) > 0]
    
    labels = [action_to_name[a] for a in actions]
    families = [action_to_family[a] for a in actions]
    vals1 = [props1.get(a, 0) for a in actions]
    vals2 = [props2.get(a, 0) for a in actions]
    
    # Chi-squared test per action with Bonferroni correction
    n_tests = len(actions)
    p_values = []
    for a in actions:
        c1 = counts1.get(a, 0)
        c2 = counts2.get(a, 0)
        rest1 = total1 - c1
        rest2 = total2 - c2
        table = [[c1, c2], [rest1, rest2]]
        if c1 + c2 > 0:
            _, p, _, _ = chi2_contingency(table)
            p_values.append(p)
        else:
            p_values.append(1.0)
    significant = [p < 0.05 / n_tests for p in p_values]
    
    y = np.arange(len(actions)) * 1.2
    h = 0.35
    
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, max(max(vals1), max(vals2)) * 1.05)
    ax.barh(y - h/2, vals1, h, label=sub1, color=sub1_color)
    ax.barh(y + h/2, vals2, h, label=sub2, color=sub2_color)
    
    for i, (label, fam, sig) in enumerate(zip(labels, families, significant)):
        star = " ★" if sig else ""
        wrapped = textwrap.fill(label + star, width=25)
        ax.annotate(
            wrapped, xy=(0, y[i]), xytext=(-10, 0),
            textcoords="offset points", ha="right", va="center", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=family_bg_colors[fam],
                      edgecolor="none", alpha=0.8),
            annotation_clip=False
        )
    
    ax.set_yticks(y)
    ax.set_yticklabels([""] * len(y))
    
    for i in range(1, len(families)):
        if families[i] != families[i - 1]:
            ax.axhline(y=(y[i] + y[i-1]) / 2, color="black", linewidth=0.8)
    
    fig.text(0.12, 0.5, "DiscoTrace Discourse Acts", va="center", ha="center",
             rotation=90, fontweight="bold", fontsize=11)
    ax.set_xlabel("proportion of answers in community with discourse act", fontweight="bold")
    ax.set_title(f"Discourse Act Usage in Answers: r/{sub1}  vs.  r/{sub2}")
    ax.legend(loc="upper right")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.subplots_adjust(left=0.25)
    plt.show()
    
    # return things needed for saving the plot as a pdf
    return fig, ax
    
    
def plot_diagonal_heatmap(
    matrix,
    title="Planner vs Humans (matched community)",
    row_prefix="planner-",
    save=False,
    save_name="diagonal.pdf",
    fig_size=(10, 1.6),
    ax=None,
    annotate_human_baseline=None,
):
    diag = {}
    for row_label in matrix.index:
        sub = row_label[len(row_prefix):] if row_label.startswith(row_prefix) else row_label
        if sub in matrix.columns:
            diag[sub] = matrix.loc[row_label, sub]
    diag = pd.Series(diag).sort_index()

    one_row = pd.DataFrame([diag.values], columns=diag.index, index=["planner ↔ human"])

    if ax is None:
        fig, ax = plt.subplots(figsize=fig_size)
        standalone = True
    else:
        standalone = False

    sns.heatmap(
        one_row, annot=True, fmt=".1f", cmap="YlOrRd",
        ax=ax, cbar_kws={"label": "Perplexity", "pad": 0.02, "shrink": 0.8},
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    ax.set_xlabel("")
    ax.set_ylabel("")
    if title:
        ax.set_title(title)

    if annotate_human_baseline:
        for i, sub in enumerate(diag.index):
            if sub in annotate_human_baseline:
                ax.text(
                    i + 0.5, 1.15,
                    f"(human: {annotate_human_baseline[sub]:.1f})",
                    ha="center", va="top", fontsize=7, color="gray",
                    transform=ax.transData,
                )

    if standalone:
        plt.tight_layout()
        if save:
            plt.savefig(save_name, bbox_inches="tight")
        plt.show()

    return diag
    


def plot_diagonal_heatmap_multi(
    matrices: dict,
    row_prefixes: dict,
    title=None,
    save=False,
    save_name="diagonal_multi.pdf",
    fig_size=(10, 2.8),
):
    rows = {}
    for row_label, matrix in matrices.items():
        prefix = row_prefixes.get(row_label, "")
        diag = {}
        for idx in matrix.index:
            sub = idx[len(prefix):] if prefix and idx.startswith(prefix) else idx
            if sub in matrix.columns:
                diag[sub] = matrix.loc[idx, sub]
        rows[row_label] = pd.Series(diag)

    df = pd.DataFrame(rows).T
    df = df.reindex(sorted(df.columns), axis=1)

    fig, ax = plt.subplots(figsize=fig_size)
    sns.heatmap(
        df, annot=True, fmt=".1f", cmap="YlOrRd",
        ax=ax, cbar_kws={"label": "Perplexity", "pad": 0.02, "shrink": 0.8},
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    ax.set_xlabel("")
    ax.set_ylabel("")
    if title:
        ax.set_title(title)

    plt.tight_layout()
    if save:
        plt.savefig(save_name, bbox_inches="tight")
    plt.show()
    return df

