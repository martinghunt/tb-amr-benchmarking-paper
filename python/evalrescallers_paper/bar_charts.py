
import csv
import os
import subprocess
import textwrap


def make_res_or_susc_samples_bar_chart(r_or_s, infile, dataset, tools, drugs, outprefix, y_axis_label=""):
    '''dataset = string containing dataset name to plot.
    tools = OrderedDict. Key = tool, value = colour to use when plotting.
    drugs = OrderedDict. Key = Drug in file, value = string to use for x labels in plot
    '''
    if r_or_s == 'R':
        y_calc1 = 'TOTAL'
        y_calc2 = 'TP+FN'
        y_calc3 = 'TP'
    elif r_or_s == 'S':
        y_calc1 = 'TOTAL'
        y_calc2 = 'TN+FP'
        y_calc3 = 'TN'
    else:
        raise Exception(f'r_or_s must be "R" or "S" but got {r_or_s}')

    r_script = f'{outprefix}.R'
    tsv_file = f'{outprefix}.tsv'
    tools_filter = 'd$Tool %in% c("' + '", "'.join(tools.values()) + '")'
    drugs_filter = 'd$Drug %in% c("' + '", "'.join(drugs.values()) + '")'
    scale_alpha_vect = 'c(' + ', '.join(['1'] * len(tools)) + ')'


    # In rare cases, possible that a tool completely failed. If this happens,
    # the total samples will be too small and the FAIL_{R,S} will not have
    # been incremented. Height of all the bars should be the same for
    # one drug. Use the max total samples across the tools. Put this in
    # a new column called TOTAL.
    samples_per_drug = {d: 0 for d in drugs}
    with open(infile) as f:
        reader = csv.DictReader(f, delimiter='\t')
        tsv_out = [list(reader.fieldnames)]
        for d in reader:
            if d['Tool'] not in tools or d['Drug'] not in drugs or d['Dataset'] != dataset:
                continue

            if r_or_s == 'R':
                total_samples = int(d['TP']) + int(d['FN']) + int(d['FAIL_R'])
            else:
                total_samples = int(d['TN']) + int(d['FP']) + int(d['FAIL_S'])
            samples_per_drug[d['Drug']] = max(samples_per_drug[d['Drug']], total_samples)
            tsv_out.append(d)

    with open(tsv_file, 'w') as f:
        print(*tsv_out[0], 'TOTAL', sep='\t', file=f)
        for d in tsv_out[1:]:
            total = samples_per_drug[d['Drug']]
            d['Drug'] = drugs[d['Drug']]
            d['Tool'] = tools[d['Tool']]
            print(*d.values(), total, sep='\t', file=f)



    with open(r_script, 'w') as f:
        print(textwrap.dedent(r'''
            library(ggplot2)
            fail_colour <- "black"
            wrong_call_colour <- "red"
            d <- read.csv("''' + tsv_file + r'''", sep="\t", header=T)
            d <- d[d$Dataset=="''' + dataset + '" & ' + tools_filter + ' & ' + drugs_filter + r''',]
            d <- with(d, d[order(Drug, Tool),])
            pdf("''' + outprefix + r'''.pdf")
            ggplot(data=d) +
                geom_bar(stat="identity",position="dodge",fill=fail_colour,colour="black",aes(x=Drug, y=''' + y_calc1 + r''',alpha=Tool)) +
                geom_bar(stat="identity",position="dodge",fill=wrong_call_colour,colour="black",aes(x=Drug, y=''' + y_calc2 + r''',alpha=Tool)) +
                geom_bar(stat="identity",position="dodge",colour="black",aes(x=Drug, y=''' + y_calc3 + r''',fill=Tool)) +
                scale_alpha_manual('',values=''' + scale_alpha_vect + r''',guide=FALSE) +
                ylab("''' + y_axis_label + r'''") +
                xlab("")
            dev.off()'''), file=f)

    command = f'R CMD BATCH {r_script}'
    subprocess.check_output(command, shell=True)
    os.unlink(f'{r_script}out')


def make_res_susc_bar_charts(infile, datasets, tools, drugs, outprefix):
    for dataset in datasets:
        for r_or_s in ['R', 'S']:
            out = f'{outprefix}.{dataset}.{r_or_s}'
            y_axis_label = {'R': 'Resistant', 'S': 'Susceptible'}[r_or_s] + ' Samples'
            make_res_or_susc_samples_bar_chart(r_or_s, infile, dataset, tools, drugs, out, y_axis_label=y_axis_label)



