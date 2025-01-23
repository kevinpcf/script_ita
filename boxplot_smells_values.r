library(jsonlite)

smells_values <- fromJSON("smells_values.json", flatten=TRUE)
attach(smells_values)

type_smell <- names(smells_values)

for (ts in type_smell) {
	smell_values <- smells_values[[ts]]
	if (length(smell_values) > 0) {
		title_jpeg <- paste('Grunt_',ts,'_rboxplot.jpg',sep = '')
		jpeg(title_jpeg)
		boxplot(smell_values, xlab = "Smells", ylab = "Smell Weight", outline = FALSE)
		dev.off()
	}
}

detach(smells_values)